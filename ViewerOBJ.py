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

angle_x = 30.0
angle_y = -45.0
zoom = 150.0
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

def load_texture_image(image_path):
    im = Image.open(image_path)
    im = im.convert('RGBA')
    ix, iy = im.size
    image_data = im.tobytes("raw", "RGBA", 0, -1)
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ix, iy, 0, GL_RGBA,
                 GL_UNSIGNED_BYTE, image_data)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tid

def init_textures():
    global texture_ids, scene
    texture_ids.clear()
    if scene is None:
        return
    for name, material in scene.materials.items():
        if material.texture is not None:
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
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y
            if z < min_z: min_z = z
            if z > max_z: max_z = z

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
        vertex_format = material.vertex_format  # ex: 'T2F_N3F_V3F'
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
        vbo_dict[name] = (vbo, material.texture, stride, has_texcoords, has_normals, has_vertices)

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
    global vbo_dict, texture_ids
    for name, (vbo, texture, stride, has_texcoords, has_normals, has_vertices) in vbo_dict.items():
        if texture is not None and texture in texture_ids:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_ids[texture])
        else:
            glDisable(GL_TEXTURE_2D)
        vbo.bind()
        glEnableClientState(GL_VERTEX_ARRAY)
        offset = 0
        if has_texcoords:
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
        if texture is not None and texture in texture_ids:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)

def display():
    global rotation_x, rotation_y, rotation_z
    global pos_x, pos_y, pos_z
    global scale_x, scale_y, scale_z
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    cam_x = zoom * np.cos(np.radians(angle_y)) * np.cos(np.radians(angle_x))
    cam_y = zoom * np.sin(np.radians(angle_x))
    cam_z = zoom * np.sin(np.radians(angle_y)) * np.cos(np.radians(angle_x))
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)
    glLightfv(GL_LIGHT0, GL_POSITION, [100, 100, 100, 1])
    glPushMatrix()
    
    
    if (Qwireframe) : glPolygonMode(GL_FRONT_AND_BACK, GL_LINE) 

    glTranslatef(pos_x, pos_y, pos_z)

    glRotatef(rotation_x, 1.0, 0.0, 0.0)
    glRotatef(rotation_y, 0.0, 1.0, 0.0)
    glRotatef(rotation_z, 0.0, 0.0, 1.0)

    glScalef(scale_x, scale_y, scale_z)

    draw_scene()
    
    if (Qwireframe) : glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    glPopMatrix()
    glutSwapBuffers()

def idle():
    glutPostRedisplay()

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
    global rotation_x, rotation_y, rotation_z
    global pos_x, pos_y, pos_z
    global scale_x, scale_y, scale_z
    deltaR = 1.0
    deltaP = 1.0
    try:
        key = key.decode("utf-8")
        if key == '\x1b' or key == 'q':  # ESC or q
            print("Close Esc or Q")
            try:
                glutLeaveMainLoop()
            except NameError:
                window = glutGetWindow()
                glutDestroyWindow(window)
            sys.exit(0)
        elif key == 'w': 
            global Qwireframe
            Qwireframe = not Qwireframe
        elif key == '8':
            pos_y += deltaP
            print("position (x,z,z) = ("+str(pos_x)+","+str(pos_y)+","+str(pos_z)+")")
        elif key == '2':
            pos_y -= deltaP
            print("position (x,z,z) = ("+str(pos_x)+","+str(pos_y)+","+str(pos_z)+")")
        elif key == '4':
            pos_x -= deltaP
            print("position (x,z,z) = ("+str(pos_x)+","+str(pos_y)+","+str(pos_z)+")")
        elif key == '6':
            pos_x += deltaP
            print("position (x,z,z) = ("+str(pos_x)+","+str(pos_y)+","+str(pos_z)+")")
        elif key == '7':
            pos_z -= deltaP
            print("position (x,z,z) = ("+str(pos_x)+","+str(pos_y)+","+str(pos_z)+")")
        elif key == '9':
            pos_z += deltaP
            print("position (x,z,z) = ("+str(pos_x)+","+str(pos_y)+","+str(pos_z)+")")
        elif key == 'z':
            rotation_z += deltaR 
            print("rotation (x,z,z) = ("+str(rotation_x)+","+str(rotation_y)+","+str(rotation_z)+")")
        elif key == 'Z':
            rotation_z -= deltaR 
            print("rotation (x,z,z) = ("+str(rotation_x)+","+str(rotation_y)+","+str(rotation_z)+")")
        elif key == 'x':
            rotation_x += deltaR 
            print("rotation (x,z,z) = ("+str(rotation_x)+","+str(rotation_y)+","+str(rotation_z)+")")
        elif key == 'X':
            rotation_x -= deltaR 
            print("rotation (x,z,z) = ("+str(rotation_x)+","+str(rotation_y)+","+str(rotation_z)+")")
        elif key == 'y':
            rotation_y += deltaR 
            print("rotation (x,z,z) = ("+str(rotation_x)+","+str(rotation_y)+","+str(rotation_z)+")")
        elif key == 'Y':
            rotation_y -= deltaR 
            print("rotation (x,z,z) = ("+str(rotation_x)+","+str(rotation_y)+","+str(rotation_z)+")")
        elif key == '+':
            scale_x *= 1.1
            scale_y *= 1.1
            scale_z *= 1.1
            print("scale (x,z,z) = ("+str(scale_x)+","+str(scale_y)+","+str(scale_z)+")")
        elif key == '-':
            scale_x /= 1.1
            scale_y /= 1.1
            scale_z /= 1.1
            print("scale (x,z,z) = ("+str(scale_x)+","+str(scale_y)+","+str(scale_z)+")")
        glutPostRedisplay()
    except SystemExit:
        pass

def main():
    global scene
    scene = pywavefront.Wavefront(obj_path, create_materials=True, collect_faces=True, strict=False)
    bbox = calculate_bounding_box()
    print(f"Bounding box : X[{bbox[0]}, {bbox[1]}], Y[{bbox[2]}, {bbox[3]}], Z[{bbox[4]}, {bbox[5]}]")
    
    polygons, triangles, vertices = count_mesh_elements()
    print(f"Polygones : {polygons}, Triangles : {triangles}, Vertices : {vertices}")


    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
        
    if QFullScreen:
        glutCreateWindow(b"Load OBJ multitexture optimise VBO")
        glutFullScreen()
    else:        
        glutInitWindowSize(800, 600)
        glutCreateWindow(b"Load OBJ multitexture optimise VBO")
    
    
    
    init()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutKeyboardFunc(keyboard)
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
    QFullScreen=args.Fullscreen
    
    main()
    

