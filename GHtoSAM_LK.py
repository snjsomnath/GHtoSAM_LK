import Rhino.Geometry as rg
import collections
import math
import os

def validate_inputs(trees, arrays, buildings):
    """
    Validates the inputs for their respective types and conditions.
    
    :param trees: List of rg.Point3d representing trees.
    :param arrays: List of rg.Surface or rg.Brep representing solar arrays.
    :param buildings: List of rg.Box representing buildings.
    :return: True if all inputs are valid, False otherwise.
    """
    # Check if inputs are iterable
    if not all(isinstance(x, collections.Iterable) for x in [trees, arrays, buildings]):
        print("Error: One of the inputs is not iterable.")
        return False

    # Check trees
    for i, tree in enumerate(trees):
        if not isinstance(tree, rg.Point3d):
            print("Error: Tree at index {} is not a Rhino Point3d.".format(i))
            return False

    # Check arrays
    for i, array in enumerate(arrays):
        if not isinstance(array, (rg.Surface, rg.Brep)):
            print("Error: Array at index {} is not a Rhino Surface or Brep.".format(i))
            return False
        
        # Convert Breps to Surfaces for consistency
        if isinstance(array, rg.Brep) and array.Faces.Count == 1:
            array = array.Faces[0].ToNurbsSurface()
        
        # Check if the surface is valid
        if not array.IsValid:
            print("Error: Surface at index {} is not valid.".format(i))
            return False

        # Check the normal direction
        centroid = rg.AreaMassProperties.Compute(array).Centroid
        success, u, v = array.ClosestPoint(centroid)
        if success:
            normal = array.NormalAt(u, v)
            if normal.Z < 0:  # If pointing downwards
                print("Error: Surface at index {} has a normal pointing in a negative direction.".format(i))
                return False

    # Check buildings
    for i, building in enumerate(buildings):
        if not isinstance(building, rg.Box):
            print("Error: Building at index {} is not a Rhino Box.".format(i))
            return False
    
        if not building.IsValid:
            print("Error: Building at index {} is not a valid Box.".format(i))
            return False
    
    return True

def get_trimming_rectangle_dimensions(surface):
    """
    Extract the trimming rectangle dimensions of the provided surface.

    :param surface: A Rhino Surface.
    :return: width and length of the trimming rectangle.
    """
    # Convert the surface to a Brep for edge extraction
    brep_form = surface.ToBrep()
    edge_curves = brep_form.DuplicateEdgeCurves()
    x, y = edge_curves[1], edge_curves[0]
    width, length = x.GetLength(), y.GetLength()
    return width, length

def surface_to_panel(surface, i):
    """
    Converts a surface into a panel with properties.

    :param surface: A Rhino Surface representing the panel.
    :param i: Index or identifier for the panel.
    :return: String in LKscript format.
    """
    # Compute the normal vector at the centroid of the surface
    centroid = rg.AreaMassProperties.Compute(surface).Centroid
    success, u, v = surface.ClosestPoint(centroid)
    if not success:
        return ""  # Return an empty string if there's an issue
    normal = surface.NormalAt(u, v)
    normal.Unitize()
    
    # Compute azimuth
    projected_normal = rg.Vector3d(normal.X, normal.Y, 0)
    azimuth = rg.Vector3d.VectorAngle(rg.Vector3d.YAxis, projected_normal)
    if normal.X < 0:  # West of North
        azimuth = 2 * math.pi - azimuth
    azimuth = math.degrees(azimuth)  # Convert to degrees
    
    # Compute tilt
    tilt = math.degrees(rg.Vector3d.VectorAngle(normal, rg.Vector3d.ZAxis))
    
    width, length = get_trimming_rectangle_dimensions(surface)
    # Return the corresponding LKscript code
    return "O = create('Active surface');\n" + \
           "property(O, {{Name='Panel_{}', X={}, Y={},Width = {}, Length = {}, Azimuth={}, Tilt={}}});\n".format(i,centroid.X, centroid.Y,width,length, azimuth, tilt)

    
def box_to_building(box,i):
    base_center = box.Center
    x, y, z = base_center.X, base_center.Y, 0
    width = box.X.Length
    length = box.Y.Length
    height = box.Z.Length
    
    # Calculate rotation based on orientation of one of the box's edges to X-axis
    base_plane = box.Plane
    edge_vector = base_plane.XAxis
    rotation = math.degrees(rg.Vector3d.VectorAngle(rg.Vector3d.XAxis, edge_vector))
    
    # Return the corresponding LKscript code
    return "O = create('Box');\n" + \
           "property(O, {{Name='Building_{}', X={}, Y={}, Z={}, Width={}, Length={}, Height={}, Rotation={}}});\n".format(i,x, y, z, width, length, height, rotation)


def point_to_tree(point, i):
    # Tree properties
    diameter = 20
    height = 20
    top_diameter = 8
    trunk_height = 8

    # Return the corresponding LKscript code
    return "O = create('Tree');\n" + \
           "property(O, {{Name='Tree_{}', X={}, Y={}, Z=0, Diameter={}, Height={}, TopDiameter={}, TrunkHeight={}}});\n".format(i, point.X, point.Y, diameter, height, top_diameter, trunk_height)

# Initial LKscript state
lkscript = "Please check inputs"

# Validate and generate LKscript for each object type
if not validate_inputs(trees, arrays, buildings):
    print("Input validation failed. Please correct the inputs.")
else:
    print ("Input validation successful")
    lkscript = "clear_scene();\n"
    for i, surface in enumerate(arrays):
        lkscript += surface_to_panel(surface, i)
    
    for i, building in enumerate(buildings):
        lkscript += box_to_building(building, i)
    
    for i, tree in enumerate(trees):
        lkscript += point_to_tree(tree, i)

# Path setup and file writing
if not _lk_path:
    _lk_path = "3DShading.lk"

full_path = os.path.abspath(_lk_path)
if _write_lk:
    with open(full_path, 'w') as f:
        f.write(lkscript)
        print('LK Scene successfully written to {}'.format(full_path))
    lk_path = _lk_path
else:
    lk_path = '_write_lk not set to True'