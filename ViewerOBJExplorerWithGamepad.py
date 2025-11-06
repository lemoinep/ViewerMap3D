# Author(s): Dr. Patrick Lemoine

import sys
import os
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PIL import Image
import pywavefront
import OpenGL.arrays.vbo as glvbo

Image.MAX_IMAGE_PIXELS = None

angle_x = -30.0
angle_y = -45.0
cam_pos = np.array([0.0, 5.0, 10.0], dtype=np.float32)
move_speed = 1.0

mouse_left_down = False
mouse_x, mouse_y = 0, 0

rotation_x = 0.0
rotation_y = 0.0
rotation_z = 0.0
pos_x = 0.0
pos_y = 0.0
pos_z = 0.0
scale_x = 0.1
scale_y = 0.1
scale_z = 0.1
Qwireframe = False

scene = None
texture_ids = {}
vbo_dict = {}

QFullScreen = False
QTexture = True  

def normalize(v):
    norm = np.linalg.norm(v)
    if norm > 0:
        return v / norm
    return v

def compute_camera_vectors():
    front_x = np.cos(np.radians(angle_x)) * np.sin(np.radians(angle_y))
    front_y = np.sin(np.radians(angle_x))
    front_z = np.cos(np.radians(angle_x)) * np.cos(np.radians(angle_y))
    camera_front = np.array([front_x, front_y, front_z], dtype=np.float32)
    camera_front = normalize(camera_front)

    camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    camera_right = normalize(np.cross(camera_front, camera_up))
    return camera_front, camera_right, camera_up

def load_texture_image(image_path):
    im = Image.open(image_path)
    im = im.convert('RGBA')
    ix, iy = im.size
    image_data = im.tobytes("raw", "RGBA", 0, -1)
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tid

def init_textures():
    global texture_ids, scene
    texture_ids.clear()
    if scene is None:
        return
    for name, material in scene.materials.items():
        if getattr(material, "texture", None) is not None:
            try:
                tid = load_texture_image(material.texture.path)
                texture_ids[material.texture] = tid
            except Exception as e:
                print(f"Error Load Texture {material.texture.path}: {e}")

def calculate_bounding_box():
    global scene
    if scene is None:
        return None
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    for name, material in scene.materials.items():
        vertices = material.vertices
        for i in range(0, len(vertices), 3):
            x, y, z = vertices[i], vertices[i + 1], vertices[i + 2]
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            min_z = min(min_z, z)
            max_z = max(max_z, z)
    return (min_x, max_x, min_y, max_y, min_z, max_z)

def count_mesh_elements():
    global scene
    if scene is None:
        return 0, 0, 0
    total_vertices = 0
    total_triangles = 0
    total_polygons = 0

    for name, material in scene.materials.items():
        vertices = material.vertices
        num_vertices = len(vertices) // 3
        total_vertices += num_vertices
        num_triangles = num_vertices // 3
        total_triangles += num_triangles
        total_polygons += num_triangles

    return total_polygons, total_triangles, total_vertices

def create_vbos():
    global vbo_dict, scene
    vbo_dict.clear()
    if scene is None:
        return
    for name, material in scene.materials.items():
        vertices = material.vertices
        vertex_format = material.vertex_format
        stride = 0
        has_texcoords = 'T2F' in vertex_format
        has_normals = 'N3F' in vertex_format
        has_vertices = 'V3F' in vertex_format
        if has_texcoords:
            stride += 2
        if has_normals:
            stride += 3
        if has_vertices:
            stride += 3
        if stride == 0:
            continue
        vertex_data = np.array(vertices, dtype=np.float32)
        vbo = glvbo.VBO(vertex_data)
        vbo_dict[name] = (vbo, getattr(material, "texture", None), stride, has_texcoords, has_normals, has_vertices, material)

def init():
    glClearColor(0, 0, 0, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 0.9, 0.8, 1])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1])
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    init_textures()
    create_vbos()

def reshape(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, w / float(h), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

def draw_scene():
    global vbo_dict, texture_ids, QTexture
    for name, (vbo, texture, stride, has_texcoords, has_normals, has_vertices, material) in vbo_dict.items():
        if QTexture and texture is not None and texture in texture_ids:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_ids[texture])
        else:
            glDisable(GL_TEXTURE_2D)
            # Prend toujours RGB, pas RGBA
            if hasattr(material, "diffuse") and material.diffuse is not None:
                glColor3fv(material.diffuse[:3])
            else:
                glColor3f(0.8, 0.8, 0.8)

        vbo.bind()
        glEnableClientState(GL_VERTEX_ARRAY)
        offset = 0
        if has_texcoords and QTexture:
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glTexCoordPointer(2, GL_FLOAT, stride * 4, vbo + offset)
            offset += 2 * 4
        else:
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        if has_normals:
            glEnableClientState(GL_NORMAL_ARRAY)
            glNormalPointer(GL_FLOAT, stride * 4, vbo + offset)
            offset += 3 * 4
        else:
            glDisableClientState(GL_NORMAL_ARRAY)
        if has_vertices:
            glVertexPointer(3, GL_FLOAT, stride * 4, vbo + offset)
        count = int(len(vbo) / stride)
        glDrawArrays(GL_TRIANGLES, 0, count)
        vbo.unbind()
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        if QTexture and texture is not None and texture in texture_ids:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
    glColor3f(1, 1, 1)

def display():
    global rotation_x, rotation_y, rotation_z
    global pos_x, pos_y, pos_z
    global scale_x, scale_y, scale_z
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    camera_front, camera_right, camera_up = compute_camera_vectors()
    gluLookAt(cam_pos[0], cam_pos[1], cam_pos[2],
              cam_pos[0] + camera_front[0],
              cam_pos[1] + camera_front[1],
              cam_pos[2] + camera_front[2],
              camera_up[0], camera_up[1], camera_up[2])
    
    glLightfv(GL_LIGHT0, GL_POSITION, [100, 100, 100, 1])
    glPushMatrix()
    if Qwireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    glTranslatef(pos_x, pos_y, pos_z)
    glRotatef(rotation_x, 1.0, 0.0, 0.0)
    glRotatef(rotation_y, 0.0, 1.0, 0.0)
    glRotatef(rotation_z, 0.0, 0.0, 1.0)
    glScalef(scale_x, scale_y, scale_z)
    draw_scene()
    if Qwireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glPopMatrix()
    glutSwapBuffers()

def idle():
    glutPostRedisplay()

def mouse(button, state, x, y):
    global mouse_left_down, mouse_x, mouse_y, cam_pos
    mouse_x, mouse_y = x, y
    camera_front, camera_right, _ = compute_camera_vectors()

    if button == GLUT_LEFT_BUTTON:
        mouse_left_down = (state == GLUT_DOWN)
    elif button == 3 and state == GLUT_DOWN:  
        cam_pos += move_speed * camera_front
        glutPostRedisplay()
    elif button == 4 and state == GLUT_DOWN: 
        cam_pos -= move_speed * camera_front
        glutPostRedisplay()

def motion(x, y):
    global angle_x, angle_y, mouse_x, mouse_y
    dx = x - mouse_x
    dy = y - mouse_y
    if mouse_left_down:
        angle_y += -dx * 0.3
        angle_x += -dy * 0.3
        angle_x = np.clip(angle_x, -89, 89)
    mouse_x, mouse_y = x, y
    glutPostRedisplay()

def keyboard(key, x, y):
    global rotation_x, rotation_y, rotation_z
    global pos_x, pos_y, pos_z
    global scale_x, scale_y, scale_z
    global Qwireframe, QTexture
    deltaR = 1.0
    deltaP = 1.0
    try:
        key = key.decode("utf-8")
        if key == '\x1b' or key == 'q':
            print("Close Esc or Q")
            try:
                glutLeaveMainLoop()
            except NameError:
                window = glutGetWindow()
                glutDestroyWindow(window)
            sys.exit(0)
        elif key == 'w':
            Qwireframe = not Qwireframe
        elif key == 't':
            QTexture = not QTexture
            print(f"Mode texture : {QTexture}")
        elif key == '8':
            pos_y += deltaP
        elif key == '2':
            pos_y -= deltaP
        elif key == '4':
            pos_x -= deltaP
        elif key == '6':
            pos_x += deltaP
        elif key == '7':
            pos_z -= deltaP
        elif key == '9':
            pos_z += deltaP
        elif key == 'z':
            rotation_z += deltaR
        elif key == 'Z':
            rotation_z -= deltaR
        elif key == 'x':
            rotation_x += deltaR
        elif key == 'X':
            rotation_x -= deltaR
        elif key == 'y':
            rotation_y += deltaR
        elif key == 'Y':
            rotation_y -= deltaR
        elif key == '+':
            scale_x *= 1.1
            scale_y *= 1.1
            scale_z *= 1.1
        elif key == '-':
            scale_x /= 1.1
            scale_y /= 1.1
            scale_z /= 1.1
        glutPostRedisplay()
    except SystemExit:
        pass

def special_keys(key, x, y):
    global cam_pos
    camera_front, camera_right, _ = compute_camera_vectors()

    if key == GLUT_KEY_UP:
        cam_pos += move_speed * camera_front
        glutPostRedisplay()
    elif key == GLUT_KEY_DOWN:
        cam_pos -= move_speed * camera_front
        glutPostRedisplay()
    elif key == GLUT_KEY_LEFT:
        cam_pos -= move_speed * camera_right
        glutPostRedisplay()
    elif key == GLUT_KEY_RIGHT:
        cam_pos += move_speed * camera_right
        glutPostRedisplay()

def center_object():
    global pos_x, pos_y, pos_z
    bbox = calculate_bounding_box()
    if bbox is not None:
        center_x = (bbox[0] + bbox[1]) / 2.0
        center_y = (bbox[2] + bbox[3]) / 2.0
        center_z = (bbox[4] + bbox[5]) / 2.0
        pos_x = -center_x
        pos_y = -center_y
        pos_z = -center_z

def auto_position_camera():
    global cam_pos, angle_x, angle_y
    bbox = calculate_bounding_box()
    if bbox is not None:
        size_x = bbox[1] - bbox[0]
        size_y = bbox[3] - bbox[2] 
        size_z = bbox[5] - bbox[4]
        max_size = max(size_x, size_y, size_z)
        
        distance = max_size * 1.1 
        cam_pos = np.array([0.0, max_size * 0.5, distance], dtype=np.float32)
        angle_x = -20.0  
        angle_y = 180.0   

# =================== AJOUT GAMEPAD/JOYSTICK GLUT ===================
def joystick_func(buttonmask, x, y, z):
    global cam_pos, angle_x, angle_y, move_speed
    # Axes [-1000, 1000], centrés sur 0
    deadzone = 200
    camera_front, camera_right, _ = compute_camera_vectors()
    # Avant/arrière (y)
    if abs(y) > deadzone:
        cam_pos += (move_speed * (y / 1000.0)) * camera_front
    # Gauche/droite (x)
    if abs(x) > deadzone:
        cam_pos += (move_speed * (x / 1000.0)) * camera_right
    # Rotation horizontale caméra (z)
    if abs(z) > deadzone:
        angle_y += (z / 1000.0) * 2.0  # Sensibilité rotation
    glutPostRedisplay()
# ===================================================================

def main():
    global scene
    scene = pywavefront.Wavefront(obj_path, create_materials=True, collect_faces=True, strict=False)
    bbox = calculate_bounding_box()
    print(f"Bounding box : X[{bbox[0]}, {bbox[1]}], Y[{bbox[2]}, {bbox[3]}], Z[{bbox[4]}, {bbox[5]}]")
    polygons, triangles, vertices = count_mesh_elements()
    print(f"Polygones : {polygons}, Triangles : {triangles}, Vertices : {vertices}")
    
    center_object()
    auto_position_camera()

    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    if QFullScreen:
        glutCreateWindow(b"Load OBJ multitexture optimise VBO Explorer")
        glutFullScreen()
    else:
        glutInitWindowSize(800, 600)
        glutCreateWindow(b"Load OBJ multitexture optimise VBO Explorer")
    init()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys) 

    # =========== AJOUT CALLBACK JOYSTICK GAMEPAD ============
    try:
        if hasattr(glutJoystickFunc, '__call__'):
            glutJoystickFunc(joystick_func, 25) # Update toutes les 25ms
            print("Joystick/Gamepad GLUT activé.")
        else:
            print("Support joystick GLUT absent ou non reconnu sur cette plateforme.")
    except Exception as e:
        print("Erreur initialisation joystick GLUT: ", e)
    # ========================================================

    glutMainLoop()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--Path', type=str, default='.', help='Path.')
    parser.add_argument('--Name', type=str, default='T.obj', help='Name Obj.')
    parser.add_argument('--PosX', type=float, default=0.0, help='PosX Object.')
    parser.add_argument('--PosY', type=float, default=0.0, help='PosY Object.')
    parser.add_argument('--PosZ', type=float, default=0.0, help='PosZ Object.')
    parser.add_argument('--RotX', type=float, default=0.0, help='RotX Object.')
    parser.add_argument('--RotY', type=float, default=0.0, help='RotY Object.')
    parser.add_argument('--RotZ', type=float, default=0.0, help='RotZ Object.')
    parser.add_argument('--ScaleX', type=float, default=0.1, help='ScaleX Object.')
    parser.add_argument('--ScaleY', type=float, default=0.1, help='ScaleY Object.')
    parser.add_argument('--ScaleZ', type=float, default=0.1, help='ScaleZ Object.')
    parser.add_argument('--Fullscreen', type=int, default=0, help='Enable fullscreen mode')
    args = parser.parse_args()
    obj_path = args.Path + "/" + args.Name
    rotation_x = args.RotX
    rotation_y = args.RotY
    rotation_z = args.RotZ
    pos_x = args.PosX
    pos_y = args.PosY
    pos_z = args.PosZ
    scale_x = args.ScaleX
    scale_y = args.ScaleY
    scale_z = args.ScaleZ
    QFullScreen = bool(args.Fullscreen)
    main()
