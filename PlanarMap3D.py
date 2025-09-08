# Author(s): Dr. Patrick Lemoine

import sys
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PIL import Image

texture_path = "T.jpg"
heightmap_path = "H.jpg"
tiles_x = 200
tiles_y = 200
height_scale = 10.0
window_width, window_height = 800, 600

angle_x = -30.0
angle_y = -45.0

mouse_left_down = False
mouse_x, mouse_y = 0, 0

water_level = -0.1

cam_pos = np.array([0.0, 50.0, 0.0], dtype=np.float32)
move_speed = 1.0

vertices = None
texcoords = None
indices = None
normals = None
heightmap_data = None
texture_id = None

QFullScreen = False

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

def load_texture(path):
    im = Image.open(path).convert("RGB")
    ix, iy = im.size
    image_data = im.tobytes()
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, ix, iy, 0, GL_RGB, GL_UNSIGNED_BYTE, image_data)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tid

def load_heightmap(path):
    im = Image.open(path).convert("L")
    return np.asarray(im, dtype=np.float32) / 255.0

def compute_normals(vertices, indices):
    normals = np.zeros(vertices.shape, dtype=np.float32)
    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i], indices[i+1], indices[i+2]
        v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]
        edge1 = v1 - v0
        edge2 = v2 - v0
        n = np.cross(edge1, edge2)
        n = normalize(n)
        normals[i0] += n
        normals[i1] += n
        normals[i2] += n
    lengths = np.linalg.norm(normals, axis=1)
    nonzero = lengths > 0
    normals[nonzero] /= lengths[nonzero][:, np.newaxis]
    return normals

def generate_terrain():
    global vertices, texcoords, indices, normals
    h, w = heightmap_data.shape
    step_x = (w - 1) / tiles_x
    step_y = (h - 1) / tiles_y

    vertices = np.zeros(((tiles_x + 1) * (tiles_y + 1), 3), dtype=np.float32)
    texcoords = np.zeros(((tiles_x + 1) * (tiles_y + 1), 2), dtype=np.float32)
    indices = np.zeros(tiles_x * tiles_y * 6, dtype=np.uint32)

    idx = 0
    for j in range(tiles_y + 1):
        hm_y = int(j * step_y)
        for i in range(tiles_x + 1):
            hm_x = int(i * step_x)
            height = heightmap_data[hm_y, hm_x] * height_scale
            x = i - tiles_x / 2
            y = height
            z = j - tiles_y / 2
            vertices[idx] = [x, y, z]
            texcoords[idx] = [i / tiles_x, j / tiles_y]
            idx += 1

    idx = 0
    for j in range(tiles_y):
        for i in range(tiles_x):
            i0 = j * (tiles_x + 1) + i
            i1 = i0 + 1
            i2 = i0 + (tiles_x + 1)
            i3 = i2 + 1
            indices[idx:idx+3] = [i0, i2, i1]
            indices[idx+3:idx+6] = [i1, i2, i3]
            idx += 6

    normals = compute_normals(vertices, indices)
    
    globals()['vertices'] = vertices
    globals()['texcoords'] = texcoords
    globals()['indices'] = indices
    globals()['normals'] = normals

def init():
    global texture_id, heightmap_data
    glClearColor(0.5, 0.7, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, [0, 50, 50, 1])
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.7, 0.7, 0.7, 1])
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    texture_id = load_texture(texture_path)
    heightmap_data = load_heightmap(heightmap_path)
    generate_terrain()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, w / float(h), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

def draw_water_plane():
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.0, 0.3, 0.7, 0.5)
    size_x = tiles_x
    size_z = tiles_y
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(-size_x/2, water_level, -size_z/2)
    glVertex3f(size_x/2, water_level, -size_z/2)
    glVertex3f(size_x/2, water_level, size_z/2)
    glVertex3f(-size_x/2, water_level, size_z/2)
    glEnd()
    glDisable(GL_BLEND)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    camera_front, camera_right, camera_up = compute_camera_vectors()
    gluLookAt(cam_pos[0], cam_pos[1], cam_pos[2],
              cam_pos[0] + camera_front[0],
              cam_pos[1] + camera_front[1],
              cam_pos[2] + camera_front[2],
              camera_up[0], camera_up[1], camera_up[2])
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1, 1, 1)
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glVertexPointer(3, GL_FLOAT, 0, vertices)
    glTexCoordPointer(2, GL_FLOAT, 0, texcoords)
    glNormalPointer(GL_FLOAT, 0, normals)
    glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, indices)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisableClientState(GL_NORMAL_ARRAY)
    glBindTexture(GL_TEXTURE_2D, 0)
    draw_water_plane()
    glutSwapBuffers()

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
    global height_scale, water_level
    try:
        key = key.decode("utf-8")
        if key == '\x1b' or key == 'q':
            try:
                glutLeaveMainLoop()
            except NameError:
                window = glutGetWindow()
                glutDestroyWindow(window)
            sys.exit(0)
        elif key == '8':
            water_level += 0.1
            glutPostRedisplay()
        elif key == '2':
            water_level -= 0.1
            glutPostRedisplay()
        elif key in ("+", "="):
            height_scale += 1
            generate_terrain()
            glutPostRedisplay()
        elif key == "-":
            height_scale = max(0, height_scale - 1)
            generate_terrain()
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

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    
    if QFullScreen:
        glutCreateWindow(b"Planar Map 3D")
        glutFullScreen()
    else:        
        glutInitWindowSize(window_width, window_height)
        glutInitWindowPosition(100, 100)
        glutCreateWindow(b"Planar Map 3D")

    init()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutMainLoop()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--Path', type=str, default='.', help='Path.')
    parser.add_argument('--Texture', type=str, default='T.jpg', help='Texture.')
    parser.add_argument('--Heighmap', type=str, default='H.jpg', help='Heighmap.')
    parser.add_argument('--tiles_x', type=int, default=200, help='tiles_x.')
    parser.add_argument('--tiles_y', type=int, default=200, help='tiles_y.')
    parser.add_argument('--height_scale', type=int, default=10, help='height_scale.')
    parser.add_argument('--Fullscreen', type=int, default=0, help='Enable fullscreen mode')
    args = parser.parse_args()
    texture_path = args.Path + "/" + args.Texture
    heightmap_path = args.Path + "/" + args.Heighmap
    tiles_x = args.tiles_x
    tiles_y = args.tiles_y
    height_scale = args.height_scale
    QFullScreen=args.Fullscreen
    main()
