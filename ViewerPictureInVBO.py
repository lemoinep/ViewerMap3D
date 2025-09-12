# Author(s): Dr. Patrick Lemoine

import cv2
import numpy as np
import OpenGL.GL as gl
import glfw
import math
from OpenGL.GLU import gluPerspective, gluLookAt
import os
import sys

yaw, pitch = 0.0, 0.0
last_x, last_y = None, None
left_button_pressed = False
distance = 3.0

vbo_vertices = None
vbo_texcoords = None

def load_texture(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError("Unable to load image")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w, _ = img.shape
    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, w, h, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, img)
    gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
    return texture_id, w, h

def create_vbos(width, height):
    global vbo_vertices, vbo_texcoords
    vertices = np.array([
        [-width/2, -height/2, 0.0],
        [ width/2, -height/2, 0.0],
        [ width/2,  height/2, 0.0],
        [-width/2,  height/2, 0.0]
    ], dtype=np.float32)

    texcoords = np.array([
        [0.0, 1.0],
        [1.0, 1.0],
        [1.0, 0.0],
        [0.0, 0.0]
    ], dtype=np.float32)

    vbo_vertices = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_vertices)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    vbo_texcoords = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_texcoords)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, texcoords.nbytes, texcoords, gl.GL_STATIC_DRAW)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

def draw_quad():
    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_vertices)
    gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_texcoords)
    gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, None)
    gl.glDrawArrays(gl.GL_QUADS, 0, 4)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
    gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)

def mouse_button_callback(window, button, action, mods):
    global left_button_pressed, last_x, last_y
    if button == glfw.MOUSE_BUTTON_LEFT:
        if action == glfw.PRESS:
            left_button_pressed = True
            last_x, last_y = glfw.get_cursor_pos(window)
        elif action == glfw.RELEASE:
            left_button_pressed = False

def cursor_pos_callback(window, xpos, ypos):
    global yaw, pitch, last_x, last_y
    if left_button_pressed:
        if last_x is not None and last_y is not None:
            xoffset = xpos - last_x
            yoffset = ypos - last_y
            sensitivity = 0.3
            yaw -= xoffset * sensitivity
            pitch += yoffset * sensitivity
            pitch = max(-80, min(80, pitch))  # Strict pitch limit
        last_x, last_y = xpos, ypos

def scroll_callback(window, xoffset, yoffset):
    global distance
    distance -= yoffset * 0.1
    distance = max(0.1, min(10.0, distance))

def key_callback(window, key, scancode, action, mods):
    if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
        glfw.set_window_should_close(window, True)

def setup_projection(window_width, window_height):
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    aspect = window_width / window_height
    gluPerspective(45.0, aspect, 0.1, 100.0)
    gl.glMatrixMode(gl.GL_MODELVIEW)


def setup_spotlight():
    gl.glEnable(gl.GL_LIGHTING)
    gl.glEnable(gl.GL_LIGHT0)

    # Spotlight position (in world coordinates)
    light_position = [0.0, 0.0, 5.0, 1.0]  # Positioned above the screen

    # Spotlight direction (points towards the origin)
    spotlight_direction = [0.0, 0.0, -1.0]

    gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, light_position)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPOT_DIRECTION, spotlight_direction)

    # Spotlight cutoff angle (degrees)
    gl.glLightf(gl.GL_LIGHT0, gl.GL_SPOT_CUTOFF, 30.0)

    # Spotlight exponent (focus)
    gl.glLightf(gl.GL_LIGHT0, gl.GL_SPOT_EXPONENT, 10.0)

    # Ambient, diffuse and specular colors of the spotlight
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])


def main(image_path, enable_spotlight=False, enable_fullscreen=False):
    global distance
    if not glfw.init():
        raise RuntimeError("GLFW initialization failed")

    monitor = glfw.get_primary_monitor() if enable_fullscreen else None
    mode = glfw.get_video_mode(monitor) if enable_fullscreen else None
    width, height = (mode.size.width, mode.size.height) if enable_fullscreen else (800, 600)
    window = glfw.create_window(width, height, "OpenCV Image - OpenGL 3D VBO", monitor, None)
    
    if not window:
        glfw.terminate()
        raise RuntimeError("Window creation failed")
    glfw.make_context_current(window)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_cursor_pos_callback(window, cursor_pos_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_key_callback(window, key_callback)

    texture_id, img_w, img_h = load_texture(image_path)
    max_dim = max(img_w, img_h)
    width = img_w / max_dim
    height = img_h / max_dim
    create_vbos(width, height)

    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glEnable(gl.GL_DEPTH_TEST)

    if enable_spotlight:
        setup_spotlight()
    else:
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_LIGHT0)

    while not glfw.window_should_close(window):
        window_w, window_h = glfw.get_framebuffer_size(window)
        gl.glViewport(0, 0, window_w, window_h)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glClearColor(0.1, 0.1, 0.1, 1)
        setup_projection(window_w, window_h)
        gl.glLoadIdentity()

        cam_x = distance * math.cos(math.radians(pitch)) * math.sin(math.radians(yaw))
        cam_y = distance * math.sin(math.radians(pitch))
        cam_z = distance * math.cos(math.radians(pitch)) * math.cos(math.radians(yaw))

        gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        draw_quad()
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        glfw.swap_buffers(window)
        glfw.poll_events()

    gl.glDeleteBuffers(1, [vbo_vertices])
    gl.glDeleteBuffers(1, [vbo_texcoords])
    gl.glDeleteTextures([texture_id])
    glfw.terminate()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--Path', type=str, default='.', help='Path.')
    parser.add_argument('--Name', type=str, default='.', help='Name.')
    parser.add_argument('--Spotlight',type=int, default=0, help='Enable spotlight effect')
    parser.add_argument('--Fullscreen', type=int, default=0, help='Enable fullscreen mode')
        
    args = parser.parse_args()
    main(args.Path + "/" + args.Name, args.Spotlight, args.Fullscreen)
    
