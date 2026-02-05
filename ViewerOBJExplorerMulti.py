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

Qwireframe = False
QFullScreen = False
QTexture = True  

scene_objects = []   # List of loaded objects (Object3D instances)
texture_ids = {}     # Textures

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

class Object3D:
    def __init__(self, obj_path, pos=(0,0,0), rot=(0,0,0), scale=(0.1,0.1,0.1)):
        self.obj_path = obj_path
        self.pos = list(pos)
        self.rot = list(rot)
        self.scale = list(scale)
        self.scene = pywavefront.Wavefront(obj_path, create_materials=True, collect_faces=True, strict=False)
        self.vbo_dict = {}  
        self.init_textures()
        self.create_vbos()

    def init_textures(self):
        for name, material in self.scene.materials.items():
            if getattr(material, "texture", None) is not None:
                tex_path = material.texture.path
                if tex_path not in texture_ids:
                    try:
                        tid = load_texture_image(tex_path)
                        texture_ids[tex_path] = tid
                    except Exception as e:
                        print(f"Error loading texture {tex_path}: {e}")
        # OpenGL texture reference in each material...
        for name, material in self.scene.materials.items():
            if getattr(material, "texture", None) is not None:
                material._glid = texture_ids.get(material.texture.path)

    def create_vbos(self):
        for name, material in self.scene.materials.items():
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
            self.vbo_dict[name] = (vbo, getattr(material, "texture", None), stride, has_texcoords, has_normals, has_vertices, material)

    def draw(self):
        for name, (vbo, texture, stride, has_texcoords, has_normals, has_vertices, material) in self.vbo_dict.items():
            if QTexture and texture is not None:
                tid = texture_ids.get(texture.path)
                if tid:
                    glEnable(GL_TEXTURE_2D)
                    glBindTexture(GL_TEXTURE_2D, tid)
            else:
                glDisable(GL_TEXTURE_2D)
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
            if QTexture and texture is not None:
                glBindTexture(GL_TEXTURE_2D, 0)
                glDisable(GL_TEXTURE_2D)
        glColor3f(1, 1, 1)

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

def reshape(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, w / float(h), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

def draw_scene():
    for obj in scene_objects:
        glPushMatrix()
        glTranslatef(*obj.pos)
        glRotatef(obj.rot[0], 1, 0, 0)
        glRotatef(obj.rot[1], 0, 1, 0)
        glRotatef(obj.rot[2], 0, 0, 1)
        glScalef(*obj.scale)
        obj.draw()
        glPopMatrix()

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    camera_front, camera_right, camera_up = compute_camera_vectors()
    gluLookAt(cam_pos[0], cam_pos[1], cam_pos[2],
              cam_pos[0] + camera_front[0],
              cam_pos[1] + camera_front[1],
              cam_pos[2] + camera_front[2],
              camera_up[0], camera_up[1], camera_up[2])
    glLightfv(GL_LIGHT0, GL_POSITION, [100, 100, 100, 1])
    if Qwireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    draw_scene()
    if Qwireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
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
    global Qwireframe, QTexture
    delta_val = 1.0
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
        glutPostRedisplay()
    except SystemExit:
        pass

def special_keys(key, x, y):
    global cam_pos
    camera_front, camera_right, _ = compute_camera_vectors()
    if key == GLUT_KEY_UP:
        cam_pos += move_speed * camera_front
    elif key == GLUT_KEY_DOWN:
        cam_pos -= move_speed * camera_front
    elif key == GLUT_KEY_LEFT:
        cam_pos -= move_speed * camera_right
    elif key == GLUT_KEY_RIGHT:
        cam_pos += move_speed * camera_right
    glutPostRedisplay()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--Obj', action='append', nargs=7, metavar=('Path','Name','PosX','PosY','PosZ','RotY','Scale'),
                        help='Objet : Path Name PosX PosY PosZ RotY Scale', required=True)
    parser.add_argument('--Fullscreen', type=int, default=0, help='Enable fullscreen mode')
    args = parser.parse_args()

    # Load each object specified on the command line
    for objspec in args.Obj:
        path, name, posx, posy, posz, roty, scale = objspec
        obj_path = os.path.join(path, name)
        obj = Object3D(
            obj_path,
            pos=(float(posx), float(posy), float(posz)),
            rot=(0.0, float(roty), 0.0),
            scale=(float(scale), float(scale), float(scale))
        )
        scene_objects.append(obj)

    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    if args.Fullscreen:
        glutCreateWindow(b"Multi OBJ VBO Explorer")
        glutFullScreen()
    else:
        glutInitWindowSize(800, 600)
        glutCreateWindow(b"Multi OBJ VBO Explorer")
    init()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutMainLoop()

if __name__ == "__main__":
    main()
    # ... 

    


