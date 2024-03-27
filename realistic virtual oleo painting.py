import bpy
from math import cos, pi
from time import time, sleep
import sys, os
import cv2
import cvzone
import glob
from cvzone.FaceMeshModule import FaceMeshDetector
from cvzone.HandTrackingModule import HandDetector


bl_info = {
    "name": "DEMO Realistic Canvas",
    "blender": (3, 6, 1),
}

def is_video_device_valid(cap):
    return cap is not None and cap.isOpened()


def get_video_device(use_cam):
    for i in range(use_cam, -1, -1):
        cap = cv2.VideoCapture(i)
        if is_video_device_valid(cap):
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
        size=((len(paintings_paths)+2)*painting_separation),
        location=(-1, (len(paintings_paths)*painting_separation/2), 0.0),
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
    bpy.data.worlds['World'].use_nodes = True
    # Load HDRI
    hdri_path = hdri_path.strip('"')
    try:
        hdri = bpy.data.images.load(hdri_path)
    except:
        return "File does not exist"

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

    # Link 
    world_node_tree.links.new(coordinate_node.outputs["Generated"], node_mapping.inputs["Vector"])
    world_node_tree.links.new(node_mapping.outputs["Vector"], node_environment.inputs["Vector"])
    world_node_tree.links.new(node_environment.outputs["Color"], world_background_node.inputs["Color"])
    world_node_tree.links.new(world_background_node.outputs["Background"], world_output_node.inputs["Surface"])

    # Add image to environment
    node_environment.image = hdri

    # init_rotation = init_rotation*pi/180
    node_mapping.inputs[2].default_value[2] = init_rotation
    world_background_node.inputs["Strength"].default_value = hdri_strength

    return None

def remove_hdri():
    bpy.data.worlds['World'].use_nodes = False


def set_bulb(location):
    bpy.ops.object.light_add(type='POINT', align='WORLD', location=location, scale = (50,50,50))
    new_bulb = bpy.context.active_object

    refresh_and_get_delay()

    try:
        bpy.data.objects['bulb_empty']
    except:
        bpy.ops.object.empty_add()
        dummy = bpy.context.active_object
        dummy.name = 'bulb_empty'
    print("new_bulb", new_bulb.name)

    empty = bpy.data.objects['bulb_empty']
    new_bulb.parent = empty 

    bpy.context.view_layer.objects.active = bpy.data.objects[new_bulb.name]

    for area in bpy.context.screen.areas:
        if area.type == 'PROPERTIES':
            area.spaces[0].context = 'DATA'  

    # bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 2

    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='LIGHT')
    selected_objects = bpy.context.selected_objects
    
    return len(selected_objects)

def remove_bulbs():
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='LIGHT')
    bpy.ops.object.delete()

    try:
        bpy.data.objects['bulb_empty'].select_set(True)
        bpy.ops.object.delete()
    except:
        pass

    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 0
    
    return 0

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

# Intermidiate function
def set_viewport_render():
    space, _ = get_area_sene_context()
    space.shading.type = 'RENDERED'
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'

# Set camera to view and remove lines
def set_viewport_start(space, context, res_x, rex_y, zoom):
    space.region_3d.view_perspective = 'CAMERA'
    space.region_3d.view_camera_offset = (0.0,0.0) 
    space.region_3d.view_camera_zoom = zoom

    bpy.ops.screen.screen_full_area(use_hide_panels=True)

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
    

def move_camera(camera, current_image, desired_image, duration_frames, frame_rate, painting_separation):
    currentCameraPos = initialCameraPos = camera.location[1]
    finalCameraPos = painting_separation*desired_image
    finalCameraPos = (finalCameraPos-initialCameraPos)/2

    for i in range(duration_frames):
        currentCameraPos = -finalCameraPos * cos((pi)*i/duration_frames) + finalCameraPos + initialCameraPos
        camera.location[1] = currentCameraPos
        
        try:
            bulb_empty = bpy.data.objects['bulb_empty']
            bulb_empty.location[1] = currentCameraPos
        except:
            pass

        delay = refresh_and_get_delay(frame_rate)
        sleep(delay)        
    
    return desired_image


def handle_hands(img, faceDetector, hand_detector, current_image, camera, face, frame_rate, painting_separation, gesture_detection, hand_buffer, total_paintings):
    hands, _ = hand_detector.findHands(img, draw=False, flipType= False)
    if hands:
        hand = hands[0]
        x, y, width, height = hand["bbox"]
        lmList = hand["lmList"]
        center = hand["center"]

        if True:
            #cv2.rectangle(img, (leftCorner1), (leftCorner2), (255,0,0), 2)
            #cv2.rectangle(img, (rightCorner1), (rightCorner2), (255,0,0), 2)
            
            fingers = hand_detector.fingersUp(hand)
            desired_image = current_image
                    
            if gesture_detection == 2:
                if   (lmList[8][0] - hand_buffer["lmList"][8][0] > 8):
                    desired_image -= 1
                    gesture_detection = 1 
                    
                elif (lmList[8][0] - hand_buffer["lmList"][8][0] < -8):
                    desired_image += 1
                    gesture_detection = 0

            vertical_finger = (lmList[5][0] > lmList[2][0] and lmList[11][0] < lmList[17][0]) or (lmList[5][0] < lmList[2][0] and lmList[11][0] > lmList[17][0])

            if (fingers[1:5] == [1,0,0,0]):
                if vertical_finger and gesture_detection !=0:
                    gesture_detection = 2
            else:
                gesture_detection = 1  

            print(":", desired_image, total_paintings)
            desired_image = desired_image % total_paintings
            print("!", desired_image, total_paintings)
    
            if desired_image != current_image:
                return move_camera(camera, current_image, desired_image, 20, frame_rate, painting_separation), hand, 0
        else:
            gesture_detection = 1

        return current_image, hand, gesture_detection

    return current_image, {}, 1


def handle_faces(img, faceDetector, cap,):           
    width  = cap.get(3)
    height  = cap.get(4)
    face = False

    img, faces = faceDetector.findFaceMesh(img, draw=False)

    if faces:
        face = faces[0]
        pointLeft = face[145]
        pointRight = face[374]

        eye_center = ((pointLeft[0] + pointRight[0]) // 2, (pointLeft[1] + pointRight[1]) // 2)
        face_center = ((face[0][0] + face[2][0]) // 2, (face[0][1] + face[2][1]) // 2)

        eye_center_x = eye_center[0] -  1 * (face_center[0] - eye_center[0])
        eye_center_y = eye_center[1]

        upperBoundY = face[10][1]
        lowerBoundY = face[152][1]
        lowerRightBoundX = face[454][0]
        lowerLeftBoundX = face[234][0]

        offsetY = int((lowerBoundY - upperBoundY) *2.2 ) 

        safetyXdisplacement = 20

        offsetX, _ = faceDetector.findDistance(face[10], face[252])
        offsetX = int(offsetX * 2.5)

        left = lowerLeftBoundX - offsetX
        up = lowerBoundY
        right = lowerRightBoundX + safetyXdisplacement + offsetX
        down = lowerBoundY + offsetY
        
    else:
        up = down = left = right = 0
        eye_center_x = eye_center_y = 0
        
    eye_center_x_rad = (eye_center_x - width/2)*(pi/3) / (width/2)
    eye_center_y_rad = -(eye_center_y - height/2)*(pi/3) / (width/2)


    return eye_center_x_rad, eye_center_y_rad, (eye_center_x, eye_center_y), face, [up,down,left,right]


def set_hdri_pos(eye_center_x, eye_center_y):
    try:
        bpy.data.worlds["World"].node_tree.nodes["Mapping"].inputs[2].default_value[2] = -eye_center_x
        bpy.data.worlds["World"].node_tree.nodes["Mapping"].inputs[2].default_value[1] = eye_center_y
    except:
        pass

def set_bulb_pos(eye_center_x, eye_center_y, current_image):
    try:
        bulb_empty = bpy.data.objects['bulb_empty']
        bulb_empty.location[1] = current_image + eye_center_x
        bulb_empty.location[2] = eye_center_y
    except:
        pass


def I3D(hand_frames_skip, frame_rate, camera, painting_separation, use_cam, show_detection_view, folder_path):
    # SELECT CAMERA
    cap = get_video_device(use_cam)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 10000)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 10000)

    # INSTANCIATE Face AND Hand DETECTION MODULES
    faceDetector = FaceMeshDetector(maxFaces=1, minDetectionCon=0.3)
    hand_detector = HandDetector(detectionCon=0.4, maxHands=1, minTrackCon=0.5)
    gesture_detection = 1    # 0: Don't detect (just detected), 1: Can detect (out of box // no finger postiton), 2: detecting

    hand_buffer = {}

    print(f">> Camera Started")

    # GLOBAL CONTROL VARIABLES
    current_image = 0
    frames_count = 0
    total_paintings = len(glob.glob(os.path.join(folder_path, "*.glb")))

    print(f">> Recognition Started")

    while True:
        start_time = time()
        # CAPTURE IMAGE FROM CAMERA   
        _, img = cap.read() 
        img = cv2.flip(img, 1)   
        # img = cv2.flip(img, 0)
        # img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
        # GET FACE POSITION, in rad
        if (gesture_detection!=2):
            face_pos_x, face_pos_y, centre_point, face, hand_detect_rect = handle_faces(img, faceDetector, cap)

        crop_img = img[hand_detect_rect[0]:hand_detect_rect[1], hand_detect_rect[2]:hand_detect_rect[3]]


        # VERIFY HAND GESTURES EVERY n FPS 
        if (face and str(crop_img) != "[]" and (hand_frames_skip == 0 or gesture_detection==2 or frames_count % hand_frames_skip == 0)):
            current_image, hand_buffer, gesture_detection = handle_hands(crop_img, faceDetector, hand_detector, current_image, camera, face, frame_rate, painting_separation, gesture_detection, hand_buffer, total_paintings)         
            
            
        if current_image == -1:
            #pass
            break

        if show_detection_view:

            if hand_buffer != {}:   
                bbox = hand_buffer["bbox"]
                corner = [bbox[0] + hand_detect_rect[2], bbox[1] + hand_detect_rect[0], bbox[0] + hand_detect_rect[2] + bbox[2], bbox[1] + hand_detect_rect[0] + bbox[3]]
                lmList = hand_buffer["lmList"]
    
                if (gesture_detection == 2):
                    cv2.rectangle(img, (corner[0] - 20, corner[1] - 20),
                                (corner[2] + 20, corner[3] + 20),(255, 0, 0), 3)    
                    cv2.circle(img, (lmList[8][0] + hand_detect_rect[2], lmList[8][1]+hand_detect_rect[0]), 3, (0, 255, 0), 6)
                elif (gesture_detection == 1):
                    cv2.rectangle(img, (corner[0] - 20, corner[1] - 20),
                                (corner[2] + 20, corner[3] + 20),(220,220,220), 3) 
                    
                    for points in range(4,21,4):
                        cv2.circle(img, (lmList[points][0] + hand_detect_rect[2], lmList[points][1]+hand_detect_rect[0]), 3, (220,220,220), 6)
                else:
                    cv2.rectangle(img, (corner[0] - 20, corner[1] - 20),
                                (corner[2] + 20, corner[3] + 20),(0, 0, 255), 2) 
                    # cv2.putText(img, f"left <-", (corner[0] - 30, corner[1] - 50), cv2.FONT_HERSHEY_PLAIN,
                    #                 1, (255, 255, 255), 2)
                    
                

                # for ix, punto in enumerate(lmList):
                #     cv2.putText(img, f"{ix}", (punto[0] + hand_detect_rect[2], punto[1]+hand_detect_rect[0]), cv2.FONT_HERSHEY_PLAIN,
                #                     1, (ix*2,0,255), 2)      
                
                # cv2.putText(img, f"fingers: {hand_detector.fingersUp(hand_buffer)}", (corner[0] - 30, corner[3] + 50), cv2.FONT_HERSHEY_PLAIN,
                #                     1, (255, 255, 255), 2)

            if face:
                cv2.rectangle(img,(hand_detect_rect[2], hand_detect_rect[0]), (hand_detect_rect[3], hand_detect_rect[1]), (150, 150, 150), 2)

                cv2.rectangle(img,(face[234][0],face[10][1]), (face[454][0], face[152][1]), (255,255,255), 2)
                
                cv2.circle(img, centre_point, 4, (255,0,0), 8)
                # for ix, punto in enumerate(face):
                #     cv2.putText(img, f"{ix}", (punto[0], punto[1]), cv2.FONT_HERSHEY_PLAIN,
                #                     1, (ix*2,0,255), 1)
                
                
            
            cv2.namedWindow("Live dectection", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty("Live dectection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

            cv2.imshow("Live dectection", img)

            if cv2.waitKey(1) ==  ord('q'):
                cv2.destroyAllWindows()
                break
        else:
            try:
                pass
            except KeyboardInterrupt:
                break


        # SET ANGLE TO HDRI
        set_hdri_pos(face_pos_x, face_pos_y)
        set_bulb_pos(face_pos_x, face_pos_y, current_image)
        
        # UPDATE SCREEN and SLEEP
        frames_count += 1
        refresh_and_get_delay(frame_rate)

        # if keyboard.read_key() == "q":
        #     break

        sleep(max(0, (1/frame_rate) - (time() - start_time)))
        # print("FPS: ", round(1.0 / (time() - start_time)))

    cap.release()
    cv2.destroyAllWindows()


def start_effect(frame_rate, hand_frames_skip, zoom, cam_z_location, painting_separation, res_x, res_y, use_cam, show_detection_view, painting_path):
    location = (cam_z_location, 0, 0)
    rotation = (pi/2, 0, pi/2)

    # recommended zoom:
    #   1.25 landscape preview,
    #   62.38 portrait view
    # # # #   #########   # # # #

    camera = create_camera(location, rotation, zoom)
    space, context = get_area_sene_context()
    space = set_viewport_start(space, context, res_x, res_y, zoom)
    # WHILE LOOP
    I3D(hand_frames_skip, frame_rate, camera, painting_separation, use_cam, show_detection_view, painting_path)

    camera.location[1] = 0

    try:
        bulb_empty = bpy.data.objects['bulb_empty']
        bulb_empty.location[1] = 0
    except:
        pass

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
    
    
'''
PANEL SECTION
This part creates the interface of buttons and inputs to modify the parameters by the user
'''

# Group of internal variables
class VariablesGroup(bpy.types.PropertyGroup):
    HDRI_path:          bpy.props.StringProperty(default="C:/Users/bruno/Documents/uptpdrive/bruno_capstone/iZone/virtual_museum/poly_haven_studio_4k.hdr")
    init_rotation:      bpy.props.FloatProperty(soft_min=0, soft_max=360, default=0.0, unit="ROTATION")
    paintings_folder:   bpy.props.StringProperty(default='C:/Users/bruno/Documents/uptpdrive/bruno_capstone/virtual-oleo-painting-main/paintings-landscape')
    hdri_strength:      bpy.props.FloatProperty(soft_min=0, soft_max=10, default=1.0)
    bulb_pos_x:         bpy.props.FloatProperty(default=0.5)
    bulb_pos_y:         bpy.props.FloatProperty(default=0.0)
    bulb_pos_z:         bpy.props.FloatProperty(default=0.5)
    frame_rate:         bpy.props.IntProperty(default=60)
    hand_frames_skip:   bpy.props.IntProperty(soft_min=1, default=10)
    cam_z_location:     bpy.props.FloatProperty(default=1.801)
    paint_separation:   bpy.props.FloatProperty(default=1.5)
    camera_zoom:        bpy.props.FloatProperty(soft_min=0, default=29.20)
    res_x:              bpy.props.IntProperty(soft_min=0, default=3840)
    res_y:              bpy.props.IntProperty(soft_min=0, default=2160)
    internal_cam:       bpy.props.BoolProperty()
    detection_view:     bpy.props.BoolProperty()
    fov:                bpy.props.FloatProperty(soft_min=45, soft_max=180, default=85*pi/180, unit="ROTATION")

# Create the custom panel
class I3D_panel ():
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "I3D"
    bl_options = {'DEFAULT_CLOSED'}

### Subpanel no. 1
class INSTALL_Requirements_PT_1(I3D_panel, bpy.types.Panel):
    bl_idname = "INSTALL_Requirements_PT_1"
    bl_label = "0. Install Requirements" 
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Only install once")
        # Install all required dependencies BUTTON
        box.operator('my.install_requirements',text= "Install", icon="IMPORT")

# Install Requirements Button
class Install_Requirements_OP_ (bpy.types.Operator):
    bl_idname = 'my.install_requirements'
    bl_label = 'Install Requirements'

    def execute(self, context):
        # Install and Report status
        install_req()
        self.report({'INFO'}, "All Dependencies Installed")
        return {'FINISHED'}


### Subpanel no. 2
class SET_Environment_1_PT_(I3D_panel, bpy.types.Panel):
    bl_idname = "SET_Environment_1_PT_"
    bl_label = "1. Environment Settings" 
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout

        layout.label(text="Import Paintings", icon="RENDERLAYERS")
        box0 = layout.box()
        # Paintings path INPUT
        box0.label(text = "Paintings Folder")
        box0.prop(context.scene.custom_props, 'paintings_folder', text = '')
        row0 = box0.row()
        row0.label(text = "Separation")
        row0.prop(context.scene.custom_props, 'paint_separation', text = '')
        box0.operator('my.import_paintings', text = "Import paintings", icon="PLAY")

        layout.separator()

        layout.label(text="HDRI Options", icon="WORLD")
        box1 = layout.box()
        # HDRI path INPUT
        col1 = box1.column()
        col1.label(text = "HDR Image Path")
        col1.prop(context.scene.custom_props, 'HDRI_path', text = '')
        row1a = box1.row()
        # Initial HDRI Rotation INPUT
        row1a.label(text = "Initial Rotation")
        row1a.prop(context.scene.custom_props, 'init_rotation', text = '')
        row1b = box1.row()
        # HDRI Strenght INPUT
        row1b.label(text = "Strength")
        row1b.prop(context.scene.custom_props, 'hdri_strength', text = '')
        # Set HDRI BUTTON
        box1.operator('my.set_hdri', text= "Set HDRI", icon="PLAY")
        box1.operator('my.remove_hdri', text= "Remove HDRI", icon="TRASH")

        layout.separator()

        box2 = layout.box()
        box2.label(text="Add bulb", icon="LIGHT_SUN")
        row2a = box2.row()
        row2a.label(text = "Postition")

        col2 = row2a.column()
        col2.prop(context.scene.custom_props, 'bulb_pos_y', text = 'X')
        col2.prop(context.scene.custom_props, 'bulb_pos_z', text = 'Y')
        col2.prop(context.scene.custom_props, 'bulb_pos_x', text = 'Z')
        
        box2.operator('my.set_light_bulbs', text= "Add new Bulb", icon="ADD")
        box2.operator('my.remove_light_bulbs', text= f"Remove all Bulbs", icon="REMOVE")

# Set HDRI Button
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
        else:
            set_viewport_render()

        return {'FINISHED'}

class SET_Environment_OP_HDRI_REMOVE(bpy.types.Operator):
    bl_label = "Set Environment"          # Button label
    bl_idname = "my.remove_hdri"  # Unique identifier for the button

    def execute(self, context):
        remove_hdri()

        return {'FINISHED'}


# Set Bulbs Button  
class SET_Environment_OP_Bulb_1_(bpy.types.Operator):
    bl_label = "Set Environment"          # Button label
    bl_idname = "my.set_light_bulbs"  # Unique identifier for the button

    def execute(self, context):
        bulb_pos = (context.scene.custom_props.bulb_pos_x,
                    context.scene.custom_props.bulb_pos_y,
                    context.scene.custom_props.bulb_pos_z)
        
        bulbs_num = set_bulb(bulb_pos)

        self.report({'INFO'}, f'Total lightbulbs: {bulbs_num}')

        refresh_and_get_delay()

        return {'FINISHED'}

# Remove all Bulbs Button  
class SET_Environment_OP_Bulb_2_(bpy.types.Operator):
    bl_label = "Set Environment"          # Button label
    bl_idname = "my.remove_light_bulbs"  # Unique identifier for the button

    def execute(self, context):
        bulbs_num = remove_bulbs()

        self.report({'INFO'}, f'Total lightbulbs: {bulbs_num}')

        return {'FINISHED'}
    
# Import Paintings Button 
class SET_Environment_OP_Paintings(bpy.types.Operator):
    bl_label = "Import paintings"          # Button label
    bl_idname = "my.import_paintings"  # Unique identifier for the button
    bl_cursor_pending =  "WAIT"

    def execute(self, context):
        error, info = import_paintings(context.scene.custom_props.paintings_folder, context.scene.custom_props.paint_separation)

        if error:
            self.report({'ERROR'}, info)
        else:
            self.report({'INFO'}, info)


        set_viewport_render()

        return {'FINISHED'}


### Subpanel no.3
class START_Effect_PT_1(I3D_panel, bpy.types.Panel):
    bl_idname = "START_Effect_PT_1"
    bl_label = "2. Start Effect" 
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout

        box1 = layout.box()
        # box1.label(text = "FPS")
        row0a = box1.row()
        row0a.label(text = "Face FPS")
        row0a.prop(context.scene.custom_props, 'frame_rate', text = '')
        row0b = box1.row()
        row0b.label(text = "Hands Skip Frames")
        row0b.prop(context.scene.custom_props, 'hand_frames_skip', text = '')

        layout.label(text = "Virtual Camera options")
        box2 = layout.box()
        row1a = box2.row()
        row1a.label(text = "Zoom")
        row1a.prop(context.scene.custom_props, 'camera_zoom', text = '')
        row1b = box2.row()
        row1b.label(text = "VCam Dist")
        row1b.prop(context.scene.custom_props, 'cam_z_location', text = '')

        row1b = box2.row()

        box3 = layout.box()
        row2a = box3.row()
        row2a.label(text = "Resolution")
        col3 = row2a.column()
        col3.prop(context.scene.custom_props, 'res_x', text = 'X')
        col3.prop(context.scene.custom_props, 'res_y', text = 'Y')
        row2b = box3.row()
        row2b.label(text = 'FOV')
        row2b.prop(context.scene.custom_props, 'fov', text = '')

        layout.prop(context.scene.custom_props, 'internal_cam', text = "Use built-in camera")
        layout.prop(context.scene.custom_props, 'detection_view', text = "Show detection view")

        layout.label(text= "Check 'Rendered' Shading", icon="SHADING_RENDERED")
        layout.operator('my.start_effect',text= "Start", icon="VIEW_CAMERA")

class StartEffect(bpy.types.Operator):
    bl_label = "Start Effect"          # Button label
    bl_idname = "my.start_effect"  # Unique identifier for the button

    def execute(self, context):
        frame_rate = context.scene.custom_props.frame_rate
        hand_frames_skip = context.scene.custom_props.hand_frames_skip
        zoom = context.scene.custom_props.camera_zoom
        res_x = context.scene.custom_props.res_x
        res_y = context.scene.custom_props.res_y
        use_cam = 0 if context.scene.custom_props.internal_cam else 1
        show_detection_view = context.scene.custom_props.detection_view
        painting_separation = context.scene.custom_props.paint_separation
        cam_z_location = context.scene.custom_props.cam_z_location
        painting_path = context.scene.custom_props.paintings_folder
        
        start_effect(frame_rate, hand_frames_skip, zoom, cam_z_location, painting_separation, res_x, res_y, use_cam, show_detection_view, painting_path)

        return {'FINISHED'}

# Functional called when add-on is registered
def register():
    bpy.utils.register_class(INSTALL_Requirements_PT_1)
    bpy.utils.register_class(Install_Requirements_OP_)
    bpy.utils.register_class(SET_Environment_1_PT_)
    bpy.utils.register_class(SET_Environment_OP_HDRI)
    bpy.utils.register_class(SET_Environment_OP_HDRI_REMOVE)
    bpy.utils.register_class(SET_Environment_OP_Bulb_1_)
    bpy.utils.register_class(SET_Environment_OP_Bulb_2_)
    bpy.utils.register_class(SET_Environment_OP_Paintings)
    bpy.utils.register_class(START_Effect_PT_1)
    bpy.utils.register_class(StartEffect)

    bpy.utils.register_class(VariablesGroup)
    bpy.types.Scene.custom_props = bpy.props.PointerProperty(type=VariablesGroup)

# Functional called when add-on is unregistered
def unregister():
    # bpy.utils.register_class(ICONS_PT_)    
    bpy.utils.unregister_class(INSTALL_Requirements_PT_1)
    bpy.utils.unregister_class(Install_Requirements_OP_)
    bpy.utils.unregister_class(SET_Environment_1_PT_)
    bpy.utils.unregister_class(SET_Environment_OP_HDRI)
    bpy.utils.unregister_class(SET_Environment_OP_HDRI_REMOVE)
    bpy.utils.unregister_class(SET_Environment_OP_Bulb_1_)
    bpy.utils.unregister_class(SET_Environment_OP_Bulb_2_)
    bpy.utils.unregister_class(SET_Environment_OP_Paintings)
    bpy.utils.unregister_class(START_Effect_PT_1)
    bpy.utils.unregister_class(StartEffect)

    bpy.utils.unregister_class(VariablesGroup)
    del bpy.types.Scene.custom_props 

# register()
