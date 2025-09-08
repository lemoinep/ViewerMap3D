# Author(s): Dr. Patrick Lemoine

import sys
import os
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PIL import Image
import pyautogui

texture_path = "T.jpg"
heightmap_path = "H.jpg"

sphere_latitude_samples = 100
sphere_longitude_samples = 100
base_radius = 50.0
height_scale = 2.0

window_width = 800
window_height = 600


angle_x = 30.0
angle_y = -45.0
zoom = 150.0

mouse_left_down = False
mouse_x, mouse_y = 0, 0


vertices = None
texcoords = None
indices = None
normals = None
heightmap_data = None
texture_id = None


water_level = -0.1  

light_angle = 0.0
animate_light = True

QFullScreen = False

def load_texture(path):
    im = Image.open(path)
    im = im.convert("RGB")
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
    im = Image.open(path)
    im = im.convert("L")
    return np.asarray(im, dtype=np.float32) / 255.0

def compute_normals(vtx, idx):
    normals = np.zeros_like(vtx)
    for i in range(0, len(idx), 3):
        i0, i1, i2 = idx[i], idx[i+1], idx[i+2]
        v0, v1, v2 = vtx[i0], vtx[i1], vtx[i2]
        edge1 = v1 - v0
        edge2 = v2 - v0
        n = np.cross(edge1, edge2)
        length = np.linalg.norm(n)
        if length != 0:
            n = n / length
        normals[i0] += n
        normals[i1] += n
        normals[i2] += n
    for i in range(len(normals)):
        length = np.linalg.norm(normals[i])
        if length != 0:
            normals[i] /= length
    return normals

def get_height_from_heightmap(u, v):
    if heightmap_data is None:
        return 0.0
    h, w = heightmap_data.shape
    x = min(int(u * (w - 1)), w - 1)
    y = min(int((1.0 - v) * (h - 1)), h - 1)  # Inversion v
    return heightmap_data[y, x]

def generate_sphere():
    global vertices, texcoords, indices, normals

    vertices = []
    texcoords = []
    indices = []

    lat_samples = sphere_latitude_samples
    lon_samples = sphere_longitude_samples

    for i in range(lat_samples + 1):
        theta = np.pi * i / lat_samples
        sin_theta = np.sin(theta)
        cos_theta = np.cos(theta)

        for j in range(lon_samples + 1):
            phi = 2 * np.pi * (1 - j / lon_samples)
            sin_phi = np.sin(phi)
            cos_phi = np.cos(phi)

            u = j / lon_samples
            v = i / lat_samples

            h = get_height_from_heightmap(u, v) * height_scale

            r = base_radius + h

            x = r * sin_theta * cos_phi
            y = -r * cos_theta
            z = r * sin_theta * sin_phi

            vertices.append([x, y, z])
            texcoords.append([u, 1.0 - v])

    vertices = np.array(vertices, dtype=np.float32)
    texcoords = np.array(texcoords, dtype=np.float32)

    for i in range(lat_samples):
        for j in range(lon_samples):
            first = i * (lon_samples + 1) + j
            second = first + lon_samples + 1

            indices += [first, second, first + 1]
            indices += [second, second + 1, first + 1]

    indices = np.array(indices, dtype=np.uint32)
    normals = compute_normals(vertices, indices)

def draw_water_sphere():
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.0, 0.3, 0.8, 0.4)  

    quad = gluNewQuadric()
    gluQuadricDrawStyle(quad, GLU_FILL)
    gluQuadricNormals(quad, GLU_SMOOTH)
    gluQuadricTexture(quad, GL_FALSE)

    gluSphere(quad, base_radius + water_level, sphere_longitude_samples, sphere_latitude_samples)

    gluDeleteQuadric(quad)
    glDisable(GL_BLEND)

def init():
    global texture_id, heightmap_data

    glClearColor(0, 0, 0, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 0.9, 0.8, 1])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1])

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    texture_id = load_texture(texture_path)
    heightmap_data = load_heightmap(heightmap_path)

    generate_sphere()

def reshape(w, h):
    global window_width, window_height
    window_width, window_height = w, h
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, w / float(h), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    cam_x = zoom * np.cos(np.radians(angle_y)) * np.cos(np.radians(angle_x))
    cam_y = zoom * np.sin(np.radians(angle_x))
    cam_z = zoom * np.sin(np.radians(angle_y)) * np.cos(np.radians(angle_x))

    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

    light_pos = [
        100.0 * np.cos(np.radians(light_angle)),
        50.0,
        100.0 * np.sin(np.radians(light_angle)),
        1.0
    ]
    glLightfv(GL_LIGHT0, GL_POSITION, light_pos)

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

    draw_water_sphere()
    glutSwapBuffers()

def mouse(button, state, x, y):
    global mouse_left_down, mouse_x, mouse_y, zoom
    mouse_x, mouse_y = x, y

    if button == GLUT_LEFT_BUTTON:
        mouse_left_down = (state == GLUT_DOWN)
    elif button == 3 and state == GLUT_DOWN:
        zoom = max(10, zoom - 5)
        glutPostRedisplay()
    elif button == 4 and state == GLUT_DOWN:
        zoom = min(500, zoom + 5)
        glutPostRedisplay()

def motion(x, y):
    global angle_x, angle_y, mouse_x, mouse_y
    dx = x - mouse_x
    dy = y - mouse_y

    if mouse_left_down:
        angle_y += dx * 0.5
        angle_x += dy * 0.5
        angle_x = max(-89, min(89, angle_x))

    mouse_x, mouse_y = x, y
    glutPostRedisplay()

def keyboard(key, x, y):
    global height_scale, animate_light, water_level
    try:
        key = key.decode("utf-8")
        if key == "q" or key == "\x1b":
            print("Close Esc or Q")
            try:
                glutLeaveMainLoop()
            except NameError:
                window = glutGetWindow()
                glutDestroyWindow(window)
            sys.exit(0)
        elif key == "8":
            water_level += 0.1
            glutPostRedisplay()
        elif key == "2":
            water_level -= 0.1
            glutPostRedisplay()
        elif key == "+" or key == "=":
            height_scale += 1
            generate_sphere()
            glutPostRedisplay()
        elif key == "-":
            height_scale = max(0, height_scale - 1)
            generate_sphere()
            glutPostRedisplay()
        elif key == "l":
            animate_light = not animate_light
    except SystemExit:
        pass

def update(value):
    global light_angle
    if animate_light:
        light_angle += 1.0
        if light_angle >= 360.0:
            light_angle -= 360.0
        glutPostRedisplay()
    glutTimerFunc(30, update, 0)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    
    if QFullScreen:
        size = pyautogui.size()
        glutInitWindowSize(size.width,size.height)
        glutInitWindowPosition(0, 0)
        glutCreateWindow(b"Spherical Map 3D")
        glutFullScreen()
    else:        
        glutInitWindowSize(window_width, window_height)
        glutInitWindowPosition(100, 100)
        glutCreateWindow(b"Spherical Map 3D")
        
    init()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutKeyboardFunc(keyboard)

    glutTimerFunc(30, update, 0)

    glutMainLoop()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--Path', type=str, default='.', help='Path.')
    parser.add_argument('--Texture', type=str, default='T.jpg', help='Texture.')
    parser.add_argument('--Heighmap', type=str, default='H.jpg', help='Heighmap.')
    
    parser.add_argument('--height_scale', type=int, default=2, help='height_scale.')
    
    parser.add_argument('--sphere_latitude_samples', type=int, default=100, help='sphere_latitude_samples.')
    parser.add_argument('--sphere_longitude_samples', type=int, default=100, help='sphere_longitude_samples.')
    parser.add_argument('--Fullscreen', type=int, default=0, help='Enable fullscreen mode')
    
    
    args = parser.parse_args()
    texture_path = args.Path+"/"+args.Texture
    heightmap_path = args.Path+"/"+args.Heighmap
    
    height_scale = args.height_scale
    
    sphere_latitude_samples = args.sphere_latitude_samples
    sphere_longitude_samples = args.sphere_longitude_samples
    QFullScreen=args.Fullscreen
    
    main()
