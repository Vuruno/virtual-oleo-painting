import bpy
from math import cos, radians, pi
from time import time, sleep, ctime
import sys, os
# pip install pywin32
import win32gui
import win32con
import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
from cvzone.HandTrackingModule import HandDetector

bl_info = {
    "name": "DEMO 1 3DI",
    "blender": (3, 6, 1),
}

def is_video_device_valid(cap):
    return cap is not None and cap.isOpened()


def get_video_device(use_cam):
    for i in range(use_cam, -1, -1):
        cap = cv2.VideoCapture(i)
        if is_video_device_valid(cap):
            print("AAAAAAAAAAAAAAAAAAA ", i)
            return cap
        cap.release()
    return None
 
# IMPORT AND PLACE PAINTINGS
def import_paintings(folder, painting_separation):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='EMPTY')
    bpy.ops.object.delete()
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()

    folder_path = folder
    try:
        paintings_paths = [f"{folder_path}/{paint_name}" for paint_name in sorted(os.listdir(folder_path)) if paint_name[-3:] == "glb"]
    except:
        return (True, "Folder does not exist")

    if len(paintings_paths) < 1:
        return (True, "Folder does not contain .glb assets")

    for painting_number, path_full_painting in enumerate(paintings_paths):
        print_disable()
        bpy.ops.import_scene.gltf(filepath=path_full_painting)
        print_enable()
        
        for obj in bpy.context.selected_objects:
            obj.select_set(True)
            
        bpy.context.object.location[1] = painting_separation * painting_number
    
    bpy.ops.mesh.primitive_plane_add(
        size=(len(paintings_paths)+2),
        location=(-1, (len(paintings_paths)/2), 0.0),
        rotation=(0.0, pi/2, 0.0)
    )
    obj = bpy.context.object
    obj.color = (0,0,0,0)
    
    # Create a material
    mat = bpy.data.materials.new("Black")

    # Activate its nodes
    mat.use_nodes = True

    # Get the principled BSDF (created by default)
    principled = mat.node_tree.nodes['Principled BSDF']

    # Assign the color
    principled.inputs['Base Color'].default_value = (0,0,0,1)
    principled.inputs[7].default_value = 0
    principled.inputs[9].default_value = 0
    principled.inputs[15].default_value = 0

    # Assign the material to the object
    obj.data.materials.append(mat)

    return (False, "Paintings Placed")

# Disable console printing
def print_disable():
    sys.stdout = open(os.devnull, 'w')

# Restore console printing
def print_enable():
    sys.stdout = sys.__stdout__

# Set HDRI environment
def set_hdri(hdri_path, hdri_strength, init_rotation):
    # Load HDRI
    hdri_path = hdri_path.strip('"')
    try:
        hdri = bpy.data.images.load(hdri_path)
    except:
        return "File does not exist"

    # Remove existing lights
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='LIGHT')
    bpy.ops.object.delete()

    # Setup node environment
    world_node_tree = bpy.context.scene.world.node_tree
    world_node_tree.nodes.clear()

    # Add nodes
    coordinate_node = world_node_tree.nodes.new(type="ShaderNodeTexCoord")
    node_mapping = world_node_tree.nodes.new(type="ShaderNodeMapping")
    node_environment = world_node_tree.nodes.new(type="ShaderNodeTexEnvironment")
    world_background_node = world_node_tree.nodes.new(type="ShaderNodeBackground")
    world_output_node = world_node_tree.nodes.new(type="ShaderNodeOutputWorld")

    coordinate_node.location.x = 0
    node_mapping.location.x = 300
    node_environment.location.x = 600
    world_background_node.location.x = 900
    world_output_node.location.x = 1200

    # Link nodes
    world_node_tree.links.new(coordinate_node.outputs["Generated"], node_mapping.inputs["Vector"])
    world_node_tree.links.new(node_mapping.outputs["Vector"], node_environment.inputs["Vector"])
    world_node_tree.links.new(node_environment.outputs["Color"], world_background_node.inputs["Color"])
    world_node_tree.links.new(world_background_node.outputs["Background"], world_output_node.inputs["Surface"])

    # Add image to environment
    node_environment.image = hdri

    init_rotation = init_rotation*pi/180
    node_mapping.inputs[2].default_value[2] = init_rotation
    world_background_node.inputs["Strength"].default_value = hdri_strength

    return None

# Get variables for Scene setting
def get_area_sene_context():
    context = bpy.context.copy()
    for screen_area in bpy.context.screen.areas:
        if screen_area.type == 'VIEW_3D':
            space = screen_area.spaces.active
            if space.type == 'VIEW_3D':
                area = screen_area
                context['area'] = area
                break

    return space, context

# Set camera to view and remove lines
def set_viewport_start(space, context, res_x, rex_y, zoom):
    space.region_3d.view_perspective = 'CAMERA'
    space.region_3d.view_camera_offset = (0.0,0.0) 
    space.region_3d.view_camera_zoom = zoom

    # bpy.ops.screen.screen_full_area(context, use_hide_panels=True)

    space.shading.type = 'RENDERED'
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.eevee.taa_samples = 45

    for scene in bpy.data.scenes:
        scene.render.resolution_x = res_x
        scene.render.resolution_y = rex_y

    space.overlay.show_overlays = False
    space.show_gizmo = False
    bpy.context.scene.render.film_transparent = True

    return space

# Set viewport back to normal
def set_viewport_end(space):
    space.overlay.show_overlays = True
    space.show_gizmo = True

    bpy.context.scene.render.film_transparent = False

# Create and plane virtual camera
def create_camera(location, rotation, zoom):
    # Delete existing objects
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='CAMERA')
    bpy.ops.object.delete()

    # Create a new camera
    bpy.ops.object.camera_add(location=location,
        rotation=rotation)
                
    camera = bpy.context.object
    camera.data.type = 'PERSP' # 'ORTHO'

    bpy.context.scene.camera = camera

    bpy.context.view_layer.objects.active = camera

    return camera
    
# Render and calculate delay to get to desired FPS
def refresh_and_get_delay(frame_rate = 1, starting_ms = time()):
    print_disable() 
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    print_enable()
    ending_ms = time()

    delay = max(0, (1/frame_rate) - (ending_ms - starting_ms))
    return delay
    

def move_camera(camera, current_image, desired_image, duration_fps, frame_rate, painting_separation):
    currentCameraPos = initialCameraPos = painting_separation*current_image
    finalCameraPos = painting_separation*desired_image
    finalCameraPos = (finalCameraPos-initialCameraPos)/2

    for i in range(duration_fps):
        currentCameraPos = -finalCameraPos * cos((pi)*i/duration_fps) + finalCameraPos + initialCameraPos
        camera.location[1] = currentCameraPos
        
        delay = refresh_and_get_delay(frame_rate)
        sleep(delay)        
    
    return desired_image


def handle_hands(img, faceDetector, hand_detector, current_image, camera, face, frame_rate, painting_separation):
    hands, _ = hand_detector.findHands(img)
    if hands:
        hand = hands[0]
        x, y, width, height = hand["bbox"]

        upperBoundY = face[10][1]
        lowerBoundY = face[152][1]
        lowerRightBoundX = face[454][0]
        lowerLeftBoundX = face[234][0]
        offsetY = int((lowerBoundY - upperBoundY) * 0.5)

        safetyXdisplacement = 20
        
        offsetX, _ = faceDetector.findDistance(face[10], face[252])
        offsetX = int(offsetX) * 3

        leftCorner1 = (lowerLeftBoundX - offsetX, upperBoundY - offsetY)
        leftCorner2 = (lowerLeftBoundX - safetyXdisplacement, lowerBoundY + offsetY)
        rightCorner1 = (lowerRightBoundX + safetyXdisplacement, upperBoundY - offsetY)
        rightCorner2 = (lowerRightBoundX + safetyXdisplacement + offsetX, lowerBoundY + offsetY)

        max_width = lowerRightBoundX - lowerLeftBoundX
        min_width = max_width // 1.5
        x_hand = (x + width // 2)
        y_hand = (y + height // 2)
        isLeftXPlacementAcceptable = ((lowerLeftBoundX - offsetX) < x_hand) and (x_hand < (lowerLeftBoundX - safetyXdisplacement))
        isRightXPlacementAcceptable = ((lowerRightBoundX + safetyXdisplacement) < x_hand) and (x_hand < (lowerRightBoundX + offsetX + safetyXdisplacement))
        isYplacementAcceptable = ((upperBoundY - offsetY) < y_hand) and ((lowerBoundY + offsetY) > y_hand)
        isWidthAcceptable = (min_width <= width and width <= max_width)

        if((isLeftXPlacementAcceptable or isRightXPlacementAcceptable) and isYplacementAcceptable and isWidthAcceptable):
            fingers = hand_detector.fingersUp(hand)

            if fingers == [1,0,0,0,0]:
                return 1
            
            desired_image = fingers.count(1)-1

            if desired_image != current_image:
                move_camera(camera, current_image, desired_image, 20, frame_rate, painting_separation)

    return 0


def handle_faces(img, faceDetector, cap):           
    width  = cap.get(3)
    height  = cap.get(4)
    face = False

    _, faces = faceDetector.findFaceMesh(img, draw=False)

    if faces:
        face = faces[0]
        pointLeft = face[145]
        pointRight = face[374]

        eye_center = ((pointLeft[0] + pointRight[0]) // 2, (pointLeft[1] + pointRight[1]) // 2)
        face_center = ((face[0][0] + face[2][0]) // 2, (face[0][1] + face[2][1]) // 2)

        eye_center_x = eye_center[0] -  3 * (face_center[0] - eye_center[0])
        eye_center_y = eye_center[1]
        
    else:
        eye_center_x = eye_center_y= 0
        
    eye_center_x = (eye_center_x - width/2)*(pi/3) / (width/2)
    eye_center_y = -(eye_center_y - height/2)*(pi/3) / (width/2)

    return eye_center_x, eye_center_y, face


def set_hdri_pos(eye_center_x, eye_center_y):
    bpy.data.worlds["World"].node_tree.nodes["Mapping"].inputs[2].default_value[2] = eye_center_x
    bpy.data.worlds["World"].node_tree.nodes["Mapping"].inputs[2].default_value[1] = eye_center_y


def hdri_I3D(hand_frames_skip, frame_rate, camera, painting_separation, use_cam):
    # SELECT CAMERA
    cap = get_video_device(use_cam)

    # INSTANCIATE Face AND Hand DETECTION MODULES
    faceDetector = FaceMeshDetector(maxFaces=1)
    hand_detector = HandDetector(detectionCon=0.8, maxHands=1)

    print(f">> Camera Started")

    # GLOBAL CONTROL VARIABLES
    current_image = 0
    frames_count = 0

    print(f">> Recognition Started")


    while True:
        start_time = time()
        # CAPTURE IMAGE FROM CAMERA   
        _, img = cap.read()    
            
        # GET FACE POSITION, in rad
        face_pos_x, face_pos_y, face = handle_faces(img, faceDetector, cap)

        # VERIFY HAND GESTURES EVERY n FPS 
        if (frames_count % hand_frames_skip == 0):
            if handle_hands(img, faceDetector, hand_detector, current_image, camera, face, frame_rate, painting_separation):
                break

        # SET ANGLE TO HDRI
        set_hdri_pos(face_pos_x, face_pos_y)
        
        # UPDATE SCREEN and SLEEP
        frames_count += 1
        idle_ms = refresh_and_get_delay(frame_rate, start_time)
        sleep(idle_ms)
        print("FPS: ", round(1.0 / (time() - start_time), 1))


def start_effect(frame_rate, hand_frames_skip, zoom, location_cam, res_x, res_y, use_cam):
    location=(location_cam, 0, 0)
    rotation=(pi/2, -0, pi/2)

    painting_separation = 1

    # recommended zoom:
    #   1.25 landscape preview,
    #   62.38 portrait view
    # # # #   #########   # # # #

    camera = create_camera(location, rotation, zoom)
    space, context = get_area_sene_context()
    space = set_viewport_start(space, context, res_x, res_y, zoom)
    # WHILE LOOP
    hdri_I3D(hand_frames_skip, frame_rate, camera, painting_separation, use_cam)

    set_viewport_end(space)

    print("Program finished") 


def install_req():
    import subprocess
    import sys
    import os

    # path to python.exe
    python_exe = os.path.join(sys.prefix, 'bin', 'python.exe')
    
    # upgrade pip
    subprocess.call([python_exe, "-m", "ensurepip"])
    subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    
    # install required packages
    subprocess.call([python_exe, "-m", "pip", "install", "-r", "requirements.txt"])
    

class CustomPropertyGroup(bpy.types.PropertyGroup):
    HDRI_path:          bpy.props.StringProperty(name='Path', default="C:/Users/bruno/Documents/uptpdrive/bruno_capstone/HDR/poly_haven_studio_4k.exr")
    init_rotation:      bpy.props.IntProperty(name='Rotation (°)', soft_min=0, soft_max=360, default=0)
    paintings_folder:   bpy.props.StringProperty(name='Folder', default="C:/Users/bruno/Documents/uptpdrive/bruno_capstone/paintings")
    hdri_strength:      bpy.props.FloatProperty(name='Strength', soft_min=0, soft_max=10, default=1.0)
    bulb_pos_x:         bpy.props.FloatProperty(name='x position', default=1.5)
    bulb_pos_y:         bpy.props.FloatProperty(name='y position', default=0.5)
    frame_rate:         bpy.props.IntProperty(name='Fps', soft_min=1, default=50)
    hand_frames_skip:   bpy.props.IntProperty(name='Hand Recog fps', soft_min=1, default=6)
    cam_z_location:     bpy.props.FloatProperty(name='VCam Z Locat', default=1.801)
    camera_zoom:        bpy.props.FloatProperty(name='VCam Zoom', soft_min=0, default=62.38)
    res_x:              bpy.props.IntProperty(name='Resolution X', soft_min=0, default=2160)
    res_y:              bpy.props.IntProperty(name='Resolution Y', soft_min=0, default=3840)
    internal_cam:       bpy.props.BoolProperty(name='Built-in camera')

class I3D_panel ():
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "I3D"
    bl_options = {"HEADER_LAYOUT_EXPAND"}
    use_pin = True

class ICONS_PT_(I3D_panel, bpy.types.Panel):
    bl_idname = "ICONS_PT_"
    bl_label = "Incons:" 
    
    def draw(self, context):
        icons = ["NONE", "QUESTION", "ERROR", "CANCEL", "TRIA_RIGHT", "TRIA_DOWN", "TRIA_LEFT", "TRIA_UP", "ARROW_LEFTRIGHT", "PLUS", "DISCLOSURE_TRI_RIGHT", "DISCLOSURE_TRI_DOWN", "RADIOBUT_OFF", "RADIOBUT_ON", "MENU_PANEL", "BLENDER", "GRIP", "DOT", "COLLAPSEMENU", "X", "DUPLICATE", "TRASH", "COLLECTION_NEW", "OPTIONS", "NODE", "NODE_SEL", "WINDOW", "WORKSPACE", "RIGHTARROW_THIN", "BORDERMOVE", "VIEWZOOM", "ADD", "REMOVE", "PANEL_CLOSE", "COPY_ID", "EYEDROPPER", "CHECKMARK", "AUTO", "CHECKBOX_DEHLT", "CHECKBOX_HLT", "UNLOCKED", "LOCKED", "UNPINNED", "PINNED", "SCREEN_BACK", "RIGHTARROW", "DOWNARROW_HLT", "FCURVE_SNAPSHOT", "OBJECT_HIDDEN", "TOPBAR", "STATUSBAR", "PLUGIN", "HELP", "GHOST_ENABLED", "COLOR", "UNLINKED", "LINKED", "HAND", "ZOOM_ALL", "ZOOM_SELECTED", "ZOOM_PREVIOUS", "ZOOM_IN", "ZOOM_OUT", "DRIVER_DISTANCE", "DRIVER_ROTATIONAL_DIFFERENCE", "DRIVER_TRANSFORM", "FREEZE", "STYLUS_PRESSURE", "GHOST_DISABLED", "FILE_NEW", "FILE_TICK", "QUIT", "URL", "RECOVER_LAST", "THREE_DOTS", "FULLSCREEN_ENTER", "FULLSCREEN_EXIT", "BRUSHES_ALL", "LIGHT", "MATERIAL", "TEXTURE", "ANIM", "WORLD", "SCENE", "OUTPUT", "SCRIPT", "PARTICLES", "PHYSICS", "SPEAKER", "TOOL_SETTINGS", "SHADERFX", "MODIFIER", "BLANK1", "FAKE_USER_OFF", "FAKE_USER_ON", "VIEW3D", "GRAPH", "OUTLINER", "PROPERTIES", "FILEBROWSER", "IMAGE", "INFO", "SEQUENCE", "TEXT", "SPREADSHEET", "SOUND", "ACTION", "NLA", "PREFERENCES", "TIME", "NODETREE", "GEOMETRY_NODES", "CONSOLE", "TRACKER", "ASSET_MANAGER", "NODE_COMPOSITING", "NODE_TEXTURE", "NODE_MATERIAL", "UV", "OBJECT_DATAMODE", "EDITMODE_HLT", "UV_DATA", "VPAINT_HLT", "TPAINT_HLT", "WPAINT_HLT", "SCULPTMODE_HLT", "POSE_HLT", "PARTICLEMODE", "TRACKING", "TRACKING_BACKWARDS", "TRACKING_FORWARDS", "TRACKING_BACKWARDS_SINGLE", "TRACKING_FORWARDS_SINGLE", "TRACKING_CLEAR_BACKWARDS", "TRACKING_CLEAR_FORWARDS", "TRACKING_REFINE_BACKWARDS", "TRACKING_REFINE_FORWARDS", "SCENE_DATA", "RENDERLAYERS", "WORLD_DATA", "OBJECT_DATA", "MESH_DATA", "CURVE_DATA", "META_DATA", "LATTICE_DATA", "LIGHT_DATA", "MATERIAL_DATA", "TEXTURE_DATA", "ANIM_DATA", "CAMERA_DATA", "PARTICLE_DATA", "LIBRARY_DATA_DIRECT", "GROUP", "ARMATURE_DATA", "COMMUNITY", "BONE_DATA", "CONSTRAINT", "SHAPEKEY_DATA", "CONSTRAINT_BONE", "CAMERA_STEREO", "PACKAGE", "UGLYPACKAGE", "EXPERIMENTAL", "BRUSH_DATA", "IMAGE_DATA", "FILE", "FCURVE", "FONT_DATA", "RENDER_RESULT", "SURFACE_DATA", "EMPTY_DATA", "PRESET", "RENDER_ANIMATION", "RENDER_STILL", "LIBRARY_DATA_BROKEN", "BOIDS", "STRANDS", "GREASEPENCIL", "LINE_DATA", "LIBRARY_DATA_OVERRIDE", "GROUP_BONE", "GROUP_VERTEX", "GROUP_VCOL", "GROUP_UVS", "FACE_MAPS", "RNA", "RNA_ADD", "MOUSE_LMB", "MOUSE_MMB", "MOUSE_RMB", "MOUSE_MOVE", "MOUSE_LMB_DRAG", "MOUSE_MMB_DRAG", "MOUSE_RMB_DRAG", "MEMORY", "PRESET_NEW", "DECORATE", "DECORATE_KEYFRAME", "DECORATE_ANIMATE", "DECORATE_DRIVER", "DECORATE_LINKED", "DECORATE_LIBRARY_OVERRIDE", "DECORATE_UNLOCKED", "DECORATE_LOCKED", "DECORATE_OVERRIDE", "FUND", "TRACKER_DATA", "HEART", "ORPHAN_DATA", "USER", "SYSTEM", "SETTINGS", "OUTLINER_OB_EMPTY", "OUTLINER_OB_MESH", "OUTLINER_OB_CURVE", "OUTLINER_OB_LATTICE", "OUTLINER_OB_META", "OUTLINER_OB_LIGHT", "OUTLINER_OB_CAMERA", "OUTLINER_OB_ARMATURE", "OUTLINER_OB_FONT", "OUTLINER_OB_SURFACE", "OUTLINER_OB_SPEAKER", "OUTLINER_OB_FORCE_FIELD", "OUTLINER_OB_GROUP_INSTANCE", "OUTLINER_OB_GREASEPENCIL", "OUTLINER_OB_LIGHTPROBE", "OUTLINER_OB_IMAGE", "OUTLINER_COLLECTION", "RESTRICT_COLOR_OFF", "RESTRICT_COLOR_ON", "HIDE_ON", "HIDE_OFF", "RESTRICT_SELECT_ON", "RESTRICT_SELECT_OFF", "RESTRICT_RENDER_ON", "RESTRICT_RENDER_OFF", "RESTRICT_INSTANCED_OFF", "OUTLINER_DATA_EMPTY", "OUTLINER_DATA_MESH", "OUTLINER_DATA_CURVE", "OUTLINER_DATA_LATTICE", "OUTLINER_DATA_META", "OUTLINER_DATA_LIGHT", "OUTLINER_DATA_CAMERA", "OUTLINER_DATA_ARMATURE", "OUTLINER_DATA_FONT", "OUTLINER_DATA_SURFACE", "OUTLINER_DATA_SPEAKER", "OUTLINER_DATA_LIGHTPROBE", "OUTLINER_DATA_GP_LAYER", "OUTLINER_DATA_GREASEPENCIL", "GP_SELECT_POINTS", "GP_SELECT_STROKES", "GP_MULTIFRAME_EDITING", "GP_ONLY_SELECTED", "GP_SELECT_BETWEEN_STROKES", "MODIFIER_OFF", "MODIFIER_ON", "ONIONSKIN_OFF", "ONIONSKIN_ON", "RESTRICT_VIEW_ON", "RESTRICT_VIEW_OFF", "RESTRICT_INSTANCED_ON", "MESH_PLANE", "MESH_CUBE", "MESH_CIRCLE", "MESH_UVSPHERE", "MESH_ICOSPHERE", "MESH_GRID", "MESH_MONKEY", "MESH_CYLINDER", "MESH_TORUS", "MESH_CONE", "MESH_CAPSULE", "EMPTY_SINGLE_ARROW", "LIGHT_POINT", "LIGHT_SUN", "LIGHT_SPOT", "LIGHT_HEMI", "LIGHT_AREA", "CUBE", "SPHERE", "CONE", "META_PLANE", "META_CUBE", "META_BALL", "META_ELLIPSOID", "META_CAPSULE", "SURFACE_NCURVE", "SURFACE_NCIRCLE", "SURFACE_NSURFACE", "SURFACE_NCYLINDER", "SURFACE_NSPHERE", "SURFACE_NTORUS", "EMPTY_AXIS", "STROKE", "EMPTY_ARROWS", "CURVE_BEZCURVE", "CURVE_BEZCIRCLE", "CURVE_NCURVE", "CURVE_NCIRCLE", "CURVE_PATH", "LIGHTPROBE_CUBEMAP", "LIGHTPROBE_PLANAR", "LIGHTPROBE_GRID", "COLOR_RED", "COLOR_GREEN", "COLOR_BLUE", "TRIA_RIGHT_BAR", "TRIA_DOWN_BAR", "TRIA_LEFT_BAR", "TRIA_UP_BAR", "FORCE_FORCE", "FORCE_WIND", "FORCE_VORTEX", "FORCE_MAGNETIC", "FORCE_HARMONIC", "FORCE_CHARGE", "FORCE_LENNARDJONES", "FORCE_TEXTURE", "FORCE_CURVE", "FORCE_BOID", "FORCE_TURBULENCE", "FORCE_DRAG", "FORCE_FLUIDFLOW", "RIGID_BODY", "RIGID_BODY_CONSTRAINT", "IMAGE_PLANE", "IMAGE_BACKGROUND", "IMAGE_REFERENCE", "NODE_INSERT_ON", "NODE_INSERT_OFF", "NODE_TOP", "NODE_SIDE", "NODE_CORNER", "ANCHOR_TOP", "ANCHOR_BOTTOM", "ANCHOR_LEFT", "ANCHOR_RIGHT", "ANCHOR_CENTER", "SELECT_SET", "SELECT_EXTEND", "SELECT_SUBTRACT", "SELECT_INTERSECT", "SELECT_DIFFERENCE", "ALIGN_LEFT", "ALIGN_CENTER", "ALIGN_RIGHT", "ALIGN_JUSTIFY", "ALIGN_FLUSH", "ALIGN_TOP", "ALIGN_MIDDLE", "ALIGN_BOTTOM", "BOLD", "ITALIC", "UNDERLINE", "SMALL_CAPS", "CON_ACTION", "MOD_ENVELOPE", "MOD_OUTLINE", "MOD_LENGTH", "MOD_DASH", "MOD_LINEART", "HOLDOUT_OFF", "HOLDOUT_ON", "INDIRECT_ONLY_OFF", "INDIRECT_ONLY_ON", "CON_CAMERASOLVER", "CON_FOLLOWTRACK", "CON_OBJECTSOLVER", "CON_LOCLIKE", "CON_ROTLIKE", "CON_SIZELIKE", "CON_TRANSLIKE", "CON_DISTLIMIT", "CON_LOCLIMIT", "CON_ROTLIMIT", "CON_SIZELIMIT", "CON_SAMEVOL", "CON_TRANSFORM", "CON_TRANSFORM_CACHE", "CON_CLAMPTO", "CON_KINEMATIC", "CON_LOCKTRACK", "CON_SPLINEIK", "CON_STRETCHTO", "CON_TRACKTO", "CON_ARMATURE", "CON_CHILDOF", "CON_FLOOR", "CON_FOLLOWPATH", "CON_PIVOT", "CON_SHRINKWRAP", "MODIFIER_DATA", "MOD_WAVE", "MOD_BUILD", "MOD_DECIM", "MOD_MIRROR", "MOD_SOFT", "MOD_SUBSURF", "HOOK", "MOD_PHYSICS", "MOD_PARTICLES", "MOD_BOOLEAN", "MOD_EDGESPLIT", "MOD_ARRAY", "MOD_UVPROJECT", "MOD_DISPLACE", "MOD_CURVE", "MOD_LATTICE", "MOD_TINT", "MOD_ARMATURE", "MOD_SHRINKWRAP", "MOD_CAST", "MOD_MESHDEFORM", "MOD_BEVEL", "MOD_SMOOTH", "MOD_SIMPLEDEFORM", "MOD_MASK", "MOD_CLOTH", "MOD_EXPLODE", "MOD_FLUIDSIM", "MOD_MULTIRES", "MOD_FLUID", "MOD_SOLIDIFY", "MOD_SCREW", "MOD_VERTEX_WEIGHT", "MOD_DYNAMICPAINT", "MOD_REMESH", "MOD_OCEAN", "MOD_WARP", "MOD_SKIN", "MOD_TRIANGULATE", "MOD_WIREFRAME", "MOD_DATA_TRANSFER", "MOD_NORMALEDIT", "MOD_PARTICLE_INSTANCE", "MOD_HUE_SATURATION", "MOD_NOISE", "MOD_OFFSET", "MOD_SIMPLIFY", "MOD_THICKNESS", "MOD_INSTANCE", "MOD_TIME", "MOD_OPACITY", "REC", "PLAY", "FF", "REW", "PAUSE", "PREV_KEYFRAME", "NEXT_KEYFRAME", "PLAY_SOUND", "PLAY_REVERSE", "PREVIEW_RANGE", "ACTION_TWEAK", "PMARKER_ACT", "PMARKER_SEL", "PMARKER", "MARKER_HLT", "MARKER", "KEYFRAME_HLT", "KEYFRAME", "KEYINGSET", "KEY_DEHLT", "KEY_HLT", "MUTE_IPO_OFF", "MUTE_IPO_ON", "DRIVER", "SOLO_OFF", "SOLO_ON", "FRAME_PREV", "FRAME_NEXT", "NLA_PUSHDOWN", "IPO_CONSTANT", "IPO_LINEAR", "IPO_BEZIER", "IPO_SINE", "IPO_QUAD", "IPO_CUBIC", "IPO_QUART", "IPO_QUINT", "IPO_EXPO", "IPO_CIRC", "IPO_BOUNCE", "IPO_ELASTIC", "IPO_BACK", "IPO_EASE_IN", "IPO_EASE_OUT", "IPO_EASE_IN_OUT", "NORMALIZE_FCURVES", "ORIENTATION_PARENT", "VERTEXSEL", "EDGESEL", "FACESEL", "CURSOR", "PIVOT_BOUNDBOX", "PIVOT_CURSOR", "PIVOT_INDIVIDUAL", "PIVOT_MEDIAN", "PIVOT_ACTIVE", "CENTER_ONLY", "ROOTCURVE", "SMOOTHCURVE", "SPHERECURVE", "INVERSESQUARECURVE", "SHARPCURVE", "LINCURVE", "NOCURVE", "RNDCURVE", "PROP_OFF", "PROP_ON", "PROP_CON", "PROP_PROJECTED", "PARTICLE_POINT", "PARTICLE_TIP", "PARTICLE_PATH", "SNAP_FACE_NEAREST", "SNAP_FACE_CENTER", "SNAP_PERPENDICULAR", "SNAP_MIDPOINT", "SNAP_OFF", "SNAP_ON", "SNAP_NORMAL", "SNAP_GRID", "SNAP_VERTEX", "SNAP_EDGE", "SNAP_FACE", "SNAP_VOLUME", "SNAP_INCREMENT", "STICKY_UVS_LOC", "STICKY_UVS_DISABLE", "STICKY_UVS_VERT", "CLIPUV_DEHLT", "CLIPUV_HLT", "SNAP_PEEL_OBJECT", "GRID", "OBJECT_ORIGIN", "ORIENTATION_GLOBAL", "ORIENTATION_GIMBAL", "ORIENTATION_LOCAL", "ORIENTATION_NORMAL", "ORIENTATION_VIEW", "COPYDOWN", "PASTEDOWN", "PASTEFLIPUP", "PASTEFLIPDOWN", "VIS_SEL_11", "VIS_SEL_10", "VIS_SEL_01", "VIS_SEL_00", "AUTOMERGE_OFF", "AUTOMERGE_ON", "UV_VERTEXSEL", "UV_EDGESEL", "UV_FACESEL", "UV_ISLANDSEL", "UV_SYNC_SELECT", "GP_CAPS_FLAT", "GP_CAPS_ROUND", "FIXED_SIZE", "TRANSFORM_ORIGINS", "GIZMO", "ORIENTATION_CURSOR", "NORMALS_VERTEX", "NORMALS_FACE", "NORMALS_VERTEX_FACE", "SHADING_BBOX", "SHADING_WIRE", "SHADING_SOLID", "SHADING_RENDERED", "SHADING_TEXTURE", "OVERLAY", "XRAY", "LOCKVIEW_OFF", "LOCKVIEW_ON", "AXIS_SIDE", "AXIS_FRONT", "AXIS_TOP", "LAYER_USED", "LAYER_ACTIVE", "OUTLINER_OB_CURVES", "OUTLINER_DATA_CURVES", "CURVES_DATA", "OUTLINER_OB_POINTCLOUD", "OUTLINER_DATA_POINTCLOUD", "POINTCLOUD_DATA", "OUTLINER_OB_VOLUME", "OUTLINER_DATA_VOLUME", "VOLUME_DATA", "CURRENT_FILE", "HOME", "DOCUMENTS", "TEMP", "SORTALPHA", "SORTBYEXT", "SORTTIME", "SORTSIZE", "SHORTDISPLAY", "LONGDISPLAY", "IMGDISPLAY", "BOOKMARKS", "FONTPREVIEW", "FILTER", "NEWFOLDER", "FOLDER_REDIRECT", "FILE_PARENT", "FILE_REFRESH", "FILE_FOLDER", "FILE_BLANK", "FILE_BLEND", "FILE_IMAGE", "FILE_MOVIE", "FILE_SCRIPT", "FILE_SOUND", "FILE_FONT", "FILE_TEXT", "SORT_DESC", "SORT_ASC", "LINK_BLEND", "APPEND_BLEND", "IMPORT", "EXPORT", "LOOP_BACK", "LOOP_FORWARDS", "BACK", "FORWARD", "FILE_ARCHIVE", "FILE_CACHE", "FILE_VOLUME", "FILE_3D", "FILE_HIDDEN", "FILE_BACKUP", "DISK_DRIVE", "MATPLANE", "MATSPHERE", "MATCUBE", "MONKEY", "CURVES", "ALIASED", "ANTIALIASED", "MAT_SPHERE_SKY", "MATSHADERBALL", "MATCLOTH", "MATFLUID", "WORDWRAP_OFF", "WORDWRAP_ON", "SYNTAX_OFF", "SYNTAX_ON", "LINENUMBERS_OFF", "LINENUMBERS_ON", "SCRIPTPLUGINS", "DISC", "DESKTOP", "EXTERNAL_DRIVE", "NETWORK_DRIVE", "SEQ_SEQUENCER", "SEQ_PREVIEW", "SEQ_LUMA_WAVEFORM", "SEQ_CHROMA_SCOPE", "SEQ_HISTOGRAM", "SEQ_SPLITVIEW", "SEQ_STRIP_META", "SEQ_STRIP_DUPLICATE", "IMAGE_RGB", "IMAGE_RGB_ALPHA", "IMAGE_ALPHA", "IMAGE_ZDEPTH", "HANDLE_AUTOCLAMPED", "HANDLE_AUTO", "HANDLE_ALIGNED", "HANDLE_VECTOR", "HANDLE_FREE", "VIEW_PERSPECTIVE", "VIEW_ORTHO", "VIEW_CAMERA", "VIEW_PAN", "VIEW_ZOOM", "BRUSH_BLOB", "BRUSH_BLUR", "BRUSH_CLAY", "BRUSH_CLAY_STRIPS", "BRUSH_CLONE", "BRUSH_CREASE", "BRUSH_FILL", "BRUSH_FLATTEN", "BRUSH_GRAB", "BRUSH_INFLATE", "BRUSH_LAYER", "BRUSH_MASK", "BRUSH_MIX", "BRUSH_NUDGE", "BRUSH_PAINT_SELECT", "BRUSH_PINCH", "BRUSH_SCRAPE", "BRUSH_SCULPT_DRAW", "BRUSH_SMEAR", "BRUSH_SMOOTH", "BRUSH_SNAKE_HOOK", "BRUSH_SOFTEN", "BRUSH_TEXDRAW", "BRUSH_TEXFILL", "BRUSH_TEXMASK", "BRUSH_THUMB", "BRUSH_ROTATE", "GPBRUSH_SMOOTH", "GPBRUSH_THICKNESS", "GPBRUSH_STRENGTH", "GPBRUSH_GRAB", "GPBRUSH_PUSH", "GPBRUSH_TWIST", "GPBRUSH_PINCH", "GPBRUSH_RANDOMIZE", "GPBRUSH_CLONE", "GPBRUSH_WEIGHT", "GPBRUSH_PENCIL", "GPBRUSH_PEN", "GPBRUSH_INK", "GPBRUSH_INKNOISE", "GPBRUSH_BLOCK", "GPBRUSH_MARKER", "GPBRUSH_FILL", "GPBRUSH_AIRBRUSH", "GPBRUSH_CHISEL", "GPBRUSH_ERASE_SOFT", "GPBRUSH_ERASE_HARD", "GPBRUSH_ERASE_STROKE", "BRUSH_CURVES_ADD", "BRUSH_CURVES_COMB", "BRUSH_CURVES_CUT", "BRUSH_CURVES_DELETE", "BRUSH_CURVES_DENSITY", "BRUSH_CURVES_GROW_SHRINK", "BRUSH_CURVES_PINCH", "BRUSH_CURVES_PUFF", "BRUSH_CURVES_SLIDE", "BRUSH_CURVES_SMOOTH", "BRUSH_CURVES_SNAKE_HOOK", "KEYTYPE_KEYFRAME_VEC", "KEYTYPE_BREAKDOWN_VEC", "KEYTYPE_EXTREME_VEC", "KEYTYPE_JITTER_VEC", "KEYTYPE_MOVING_HOLD_VEC", "HANDLETYPE_FREE_VEC", "HANDLETYPE_ALIGNED_VEC", "HANDLETYPE_VECTOR_VEC", "HANDLETYPE_AUTO_VEC", "HANDLETYPE_AUTO_CLAMP_VEC", "COLORSET_01_VEC", "COLORSET_02_VEC", "COLORSET_03_VEC", "COLORSET_04_VEC", "COLORSET_05_VEC", "COLORSET_06_VEC", "COLORSET_07_VEC", "COLORSET_08_VEC", "COLORSET_09_VEC", "COLORSET_10_VEC", "COLORSET_11_VEC", "COLORSET_12_VEC", "COLORSET_13_VEC", "COLORSET_14_VEC", "COLORSET_15_VEC", "COLORSET_16_VEC", "COLORSET_17_VEC", "COLORSET_18_VEC", "COLORSET_19_VEC", "COLORSET_20_VEC", "COLLECTION_COLOR_01", "COLLECTION_COLOR_02", "COLLECTION_COLOR_03", "COLLECTION_COLOR_04", "COLLECTION_COLOR_05", "COLLECTION_COLOR_06", "COLLECTION_COLOR_07", "COLLECTION_COLOR_08", "SEQUENCE_COLOR_01", "SEQUENCE_COLOR_02", "SEQUENCE_COLOR_03", "SEQUENCE_COLOR_04", "SEQUENCE_COLOR_05", "SEQUENCE_COLOR_06", "SEQUENCE_COLOR_07", "SEQUENCE_COLOR_08", "SEQUENCE_COLOR_09", "LIBRARY_DATA_INDIRECT", "LIBRARY_DATA_OVERRIDE_NONEDITABLE", "EVENT_A", "EVENT_B", "EVENT_C", "EVENT_D", "EVENT_E", "EVENT_F", "EVENT_G", "EVENT_H", "EVENT_I", "EVENT_J", "EVENT_K", "EVENT_L", "EVENT_M", "EVENT_N", "EVENT_O", "EVENT_P", "EVENT_Q", "EVENT_R", "EVENT_S", "EVENT_T", "EVENT_U", "EVENT_V", "EVENT_W", "EVENT_X", "EVENT_Y", "EVENT_Z", "EVENT_SHIFT", "EVENT_CTRL", "EVENT_ALT", "EVENT_OS", "EVENT_F1", "EVENT_F2", "EVENT_F3", "EVENT_F4", "EVENT_F5", "EVENT_F6", "EVENT_F7", "EVENT_F8", "EVENT_F9", "EVENT_F10", "EVENT_F11", "EVENT_F12", "EVENT_ESC", "EVENT_TAB", "EVENT_PAGEUP", "EVENT_PAGEDOWN", "EVENT_RETURN", "EVENT_SPACEKEY", ]
        layout = self.layout

        for icon in icons:
            layout.label(text=icon, icon=icon)
        # layout.operator


class INSTALL_Requirements_PT_1(I3D_panel, bpy.types.Panel):
    bl_idname = "INSTALL_Requirements_PT_1"
    bl_label = "0. Install Requirements" 
    
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Only install once")
        box.operator('my.install_requirements',text= "Install", icon="IMPORT")

class Install_Requirements_OP_ (bpy.types.Operator):
    bl_idname = 'my.install_requirements'
    bl_label = 'Install Requirements'

    def execute(self, context):
        self.report({'INFO'}, "All Dependencies Installed")
        install_req()
        return {'FINISHED'}


class SET_Environment_1_PT_(I3D_panel, bpy.types.Panel):
    bl_idname = "SET_Environment_1_PT_"
    bl_label = "1. Environment Settings" 

    light_bulbs = []
    
    def draw(self, context):
        layout = self.layout

        box0 = layout.box()
        box0.label(text="Import Paintings", icon="RENDERLAYERS")
        box0.prop(context.scene.custom_props, 'paintings_folder')
        box0.operator('my.import_paintings', text = "Import paintings", icon="PLAY")

        layout.separator()

        box1 = layout.box()
        box1.label(text="HDRI Options", icon="WORLD")
        box1.prop(context.scene.custom_props, 'HDRI_path')
        row1 = box1.row()
        row1.prop(context.scene.custom_props, 'init_rotation')
        row1.prop(context.scene.custom_props, 'hdri_strength')
        box1.operator('my.set_hdri', text= "Set HDRI", icon="PLAY")

        layout.separator()

        box2 = layout.box()
        box2.label(text="Light Bulb(s) Options", icon="LIGHT_SUN")
        row2 = box2.row()
        col2 = row2.column()
        col2.prop(context.scene.custom_props, 'bulb_pos_x')
        col2.prop(context.scene.custom_props, 'bulb_pos_y')
        row2.operator('my.set_light_bulbs', text= "Add new Bulb", icon="ADD")
        box2.operator('my.set_light_bulbs', text= "Remove all Bulbs", icon="REMOVE")

class SET_Environment_OP_HDRI(bpy.types.Operator):
    bl_label = "Set Environment"          # Button label
    bl_idname = "my.set_hdri"  # Unique identifier for the button

    def execute(self, context):
        HDRI_path = context.scene.custom_props.HDRI_path
        hdri_strength = context.scene.custom_props.hdri_strength
        init_rotation = context.scene.custom_props.init_rotation
        result = set_hdri(HDRI_path, hdri_strength, init_rotation)
        if result:
            self.report({'ERROR'}, str(result))

        return {'FINISHED'}
    
class SET_Environment_OP_Bulb_1_(bpy.types.Operator):
    bl_label = "Set Environment"          # Button label
    bl_idname = "my.set_light_bulbs"  # Unique identifier for the button

    def execute(self, context):
        bulb_pos_x = context.scene.custom_props.bulb_pos_x
        bulb_pos_y = context.scene.custom_props.bulb_pos_y
        self.report({'INFO'}, str(f"{bulb_pos_x}, {bulb_pos_y}"))

        return {'FINISHED'}
    
class SET_Environment_OP_Paintings(bpy.types.Operator):
    bl_label = "Import paintings"          # Button label
    bl_idname = "my.import_paintings"  # Unique identifier for the button
    bl_cursor_pending =  "WAIT"

    def execute(self, context):
        error, info = import_paintings(context.scene.custom_props.paintings_folder, 1)

        sleep(2)

        if error:
            self.report({'ERROR'}, info)
        else:
            self.report({'INFO'}, info)


        refresh_and_get_delay()

        return {'FINISHED'}


class START_Effect_PT_1(I3D_panel, bpy.types.Panel):
    bl_idname = "START_Effect_PT_1"
    bl_label = "2. Start Effect" 
    
    def draw(self, context):
        layout = self.layout

        
        layout.label(text="Options")

        box = layout.box()
        box.label(text = "FPS")
        row0 = box.row()
        row0.prop(context.scene.custom_props, 'frame_rate', text = 'Face')
        row0.prop(context.scene.custom_props, 'hand_frames_skip', text = 'Hands')

        box2 = layout.box()
        box2.label(text = "Camera ops")
        row1 = box2.row()
        row1.prop(context.scene.custom_props, 'camera_zoom', text = 'Zoom')
        row1.prop(context.scene.custom_props, 'cam_z_location', text = 'Loc.')

        box3 = layout.box()
        box3.label(text = "Resolution")
        row2 = box3.row() 
        row2.prop(context.scene.custom_props, 'res_x', text = 'X')
        row2.prop(context.scene.custom_props, 'res_y', text = 'Y')

        layout.prop(context.scene.custom_props, 'internal_cam')

        layout.operator('my.start_effect',text= "Start", icon="VIEW_CAMERA")

class StartEffect(bpy.types.Operator):
    bl_label = "Start Effect"          # Button label
    bl_idname = "my.start_effect"  # Unique identifier for the button

    def execute(self, context):
        frame_rate = context.scene.custom_props.frame_rate
        hand_frames_skip = context.scene.custom_props.hand_frames_skip
        location_cam = context.scene.custom_props.cam_z_location
        zoom = context.scene.custom_props.camera_zoom
        res_x = context.scene.custom_props.res_x
        res_y = context.scene.custom_props.res_y
        use_cam = 0 if context.scene.custom_props.internal_cam else 1
        
        start_effect(frame_rate, hand_frames_skip, zoom, location_cam, res_x, res_y, use_cam)

        return {'FINISHED'}

# Register the panel and operator
def register():
    # bpy.utils.register_class(ICONS_PT_)    
    bpy.utils.register_class(INSTALL_Requirements_PT_1)
    bpy.utils.register_class(Install_Requirements_OP_)
    bpy.utils.register_class(SET_Environment_1_PT_)
    bpy.utils.register_class(SET_Environment_OP_HDRI)
    bpy.utils.register_class(SET_Environment_OP_Bulb_1_)
    bpy.utils.register_class(SET_Environment_OP_Paintings)
    bpy.utils.register_class(START_Effect_PT_1)
    bpy.utils.register_class(StartEffect)

    bpy.utils.register_class(CustomPropertyGroup)
    bpy.types.Scene.custom_props = bpy.props.PointerProperty(type=CustomPropertyGroup)


def unregister():
    # bpy.utils.register_class(ICONS_PT_)    
    bpy.utils.unregister_class(INSTALL_Requirements_PT_1)
    bpy.utils.unregister_class(Install_Requirements_OP_)
    bpy.utils.unregister_class(SET_Environment_1_PT_)
    bpy.utils.unregister_class(SET_Environment_OP_HDRI)
    bpy.utils.unregister_class(SET_Environment_OP_Bulb_1_)
    bpy.utils.unregister_class(SET_Environment_OP_Paintings)
    bpy.utils.unregister_class(START_Effect_PT_1)
    bpy.utils.unregister_class(StartEffect)

    bpy.utils.unregister_class(CustomPropertyGroup)
    del bpy.types.Scene.custom_props 