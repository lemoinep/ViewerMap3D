# Author(s): Dr. Patrick Lemoine with play movie

import cv2
import numpy as np
import OpenGL.GL as gl
import glfw
import math
from OpenGL.GLU import gluPerspective, gluLookAt, gluProject

yaw, pitch = 0.0, 0.0
last_x, last_y = None, None
left_button_pressed = False
distance = 3.0
vbo_vertices = None
vbo_texcoords = None
paused = False
cap = None
texture_id = None
fps = 30
fps_ori = 30
obj_pos_x, obj_pos_y, obj_pos_z = 0.0, 0.0, 0.0
obj_rot_angle_x, obj_rot_angle_y, obj_rot_angle_z = 0.0, 0.0, 0.0
obj_scale_x, obj_scale_y, obj_scale_z = 1.0, 1.0, 1.0
frame_width = None
frame_height = None

def create_vbos(width, height):
    global vbo_vertices, vbo_texcoords
    vertices = np.array([
        [-width / 2, -height / 2, 0.0],
        [width / 2, -height / 2, 0.0],
        [width / 2, height / 2, 0.0],
        [-width / 2, height / 2, 0.0]
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
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_vertices)
    gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
    gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_texcoords)
    gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, None)
    gl.glDrawArrays(gl.GL_QUADS, 0, 4)
    gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
    gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)


def mouse_button_callback(window, button, action, mods):
    global left_button_pressed, last_x, last_y, cap, paused
    if button == glfw.MOUSE_BUTTON_LEFT:
        if action == glfw.PRESS:
            left_button_pressed = True
            last_x, last_y = glfw.get_cursor_pos(window)
            result = check_video_click(window, last_x, last_y)
            if result is not None:
                video_x, video_y = result
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                if frame_count > 0 and width > 0:
                    frame_id = int((video_x / width) * (frame_count - 1))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
                    paused = False 
                    #print(f"Clic movie : coord=({int(video_x)}, {int(video_y)}) -- Go to frame {frame_id+1}/{frame_count}")
        elif action == glfw.RELEASE:
            left_button_pressed = False

def cursor_pos_callback(window, xpos, ypos):
    global yaw, pitch, last_x, last_y
    if left_button_pressed and last_x is not None and last_y is not None:
        xoffset = xpos - last_x
        yoffset = ypos - last_y
        sensitivity = 0.3
        yaw -= xoffset * sensitivity
        pitch += yoffset * sensitivity
        pitch = max(-80, min(80, pitch))
    last_x, last_y = xpos, ypos

def scroll_callback(window, xoffset, yoffset):
    global distance
    distance -= yoffset * 0.1
    distance = max(0.1, min(10.0, distance))

def key_callback(window, key, scancode, action, mods):
    global paused, yaw, pitch
    global obj_pos_x, obj_pos_y, obj_pos_z
    global fps

    if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
        glfw.set_window_should_close(window, True)
    elif key == glfw.KEY_SPACE and action == glfw.PRESS:
        paused = not paused
    if action == glfw.PRESS or action == glfw.REPEAT:
        delta_pos = 0.01
        delta_fps = 1
        if key == glfw.KEY_KP_4:
            obj_pos_x -= delta_pos
        elif key == glfw.KEY_KP_6:
            obj_pos_x += delta_pos
        elif key == glfw.KEY_KP_8:
            obj_pos_y += delta_pos
        elif key == glfw.KEY_KP_2:
            obj_pos_y -= delta_pos
        elif key == glfw.KEY_KP_9:
            fps += delta_fps*10.0
        elif key == glfw.KEY_KP_7:
            fps -= delta_fps
            fps = max(1.0,fps)
        elif key == glfw.KEY_KP_0:
            fps = fps_ori

def setup_projection(window_width, window_height):
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    aspect = window_width / window_height
    gluPerspective(45.0, aspect, 0.1, 100.0)
    gl.glMatrixMode(gl.GL_MODELVIEW)

def setup_spotlight():
    gl.glEnable(gl.GL_LIGHTING)
    gl.glEnable(gl.GL_LIGHT0)
    light_position = [0.0, 0.0, 5.0, 1.0]
    spotlight_direction = [0.0, 0.0, -1.0]
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, light_position)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPOT_DIRECTION, spotlight_direction)
    gl.glLightf(gl.GL_LIGHT0, gl.GL_SPOT_CUTOFF, 30.0)
    gl.glLightf(gl.GL_LIGHT0, gl.GL_SPOT_EXPONENT, 10.0)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])

def update_texture(frame):
    global texture_id
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, _ = frame_rgb.shape
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, w, h, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, frame_rgb)
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

def check_video_click(window, mouse_x, mouse_y):
    global frame_width, frame_height

    if frame_width is None or frame_height is None:
        return None

    quad_width = frame_width / max(frame_width, frame_height)
    quad_height = frame_height / max(frame_width, frame_height)
    quad_corners = [
        [-quad_width / 2, -quad_height / 2, 0.0],
        [ quad_width / 2, -quad_height / 2, 0.0],
        [ quad_width / 2, quad_height / 2, 0.0],
        [-quad_width / 2, quad_height / 2, 0.0],
    ]
    
    win_w, win_h = glfw.get_window_size(window)

    modelview = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
    projection = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)
    viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)

    def opengl_to_glfw_y(sy):
        return win_h - sy

    screen_corners = [
        gluProject(x, y, z, modelview, projection, viewport)
        for x, y, z in quad_corners
    ]
    screen_corners = [(sx, opengl_to_glfw_y(sy)) for sx, sy, sz in screen_corners]

    min_x = min(c[0] for c in screen_corners)
    max_x = max(c[0] for c in screen_corners)
    min_y = min(c[1] for c in screen_corners)
    max_y = max(c[1] for c in screen_corners)

    if min_x <= mouse_x <= max_x and min_y <= mouse_y <= max_y:
        u = (mouse_x - min_x) / (max_x - min_x)
        v = (mouse_y - min_y) / (max_y - min_y)
        video_x = u * frame_width
        video_y = (1 - v) * frame_height
        return (video_x, video_y)
    return None

def main(video_path, enable_spotlight=False, enable_fullscreen=False):
    global paused, cap, texture_id, vbo_vertices, vbo_texcoords, distance
    global fps, fps_ori, frame_width, frame_height

    if not glfw.init():
        raise RuntimeError("Failed to initialize GLFW")
    monitor = glfw.get_primary_monitor() if enable_fullscreen else None
    mode = glfw.get_video_mode(monitor) if enable_fullscreen else None
    window_w, window_h = (mode.size.width, mode.size.height) if enable_fullscreen else (800, 600)
    window = glfw.create_window(window_w, window_h, "OpenCV Video - OpenGL 3D VBO", monitor, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Window creation failed")
    glfw.make_context_current(window)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_cursor_pos_callback(window, cursor_pos_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_key_callback(window, key_callback)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps_ori = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened():
        glfw.terminate()
        raise RuntimeError("Unable to open video file")

    ret, frame = cap.read()
    if not ret or frame is None:
        glfw.terminate()
        raise RuntimeError("Unable to read first frame")
    frame_height, frame_width = frame.shape[:2]

    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, frame_width, frame_height, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, None)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    max_dim = max(frame_width, frame_height)
    width_norm = frame_width / max_dim
    height_norm = frame_height / max_dim
    create_vbos(width_norm, height_norm)
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LEQUAL)

    if enable_spotlight:
        setup_spotlight()
    else:
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_LIGHT0)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        if not paused:
            ret, frame = cap.read()
            cv2.waitKey(int(1000.0/fps))
            if not ret or frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            if ret and frame is not None:
                frame_height, frame_width = frame.shape[:2]
                update_texture(frame)
        gl.glViewport(0, 0, window_w, window_h)
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        setup_projection(window_w, window_h)
        gl.glLoadIdentity()
        cam_x = distance * math.cos(math.radians(pitch)) * math.sin(math.radians(yaw))
        cam_y = distance * math.sin(math.radians(pitch))
        cam_z = distance * math.cos(math.radians(pitch)) * math.cos(math.radians(yaw))
        gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

        gl.glTranslatef(obj_pos_x, obj_pos_y, obj_pos_z)
        gl.glRotatef(obj_rot_angle_x, 1, 0, 0)
        gl.glRotatef(obj_rot_angle_y, 0, 1, 0)
        gl.glRotatef(obj_rot_angle_z, 0, 0, 1)
        gl.glScalef(obj_scale_x, obj_scale_y, obj_scale_z)

        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        draw_quad()
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        glfw.swap_buffers(window)

    cap.release()
    gl.glDeleteBuffers(1, [vbo_vertices])
    gl.glDeleteBuffers(1, [vbo_texcoords])
    gl.glDeleteTextures([texture_id])
    glfw.terminate()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--Path', type=str, default='.', help='Video file folder path')
    parser.add_argument('--Name', type=str, default='video.mp4', help='Video file name')
    parser.add_argument('--Spotlight', type=int, default=0, help='Enable spotlight effect (1 or 0)')
    parser.add_argument('--Fullscreen', type=int, default=0, help='Enable fullscreen mode (1 or 0)')
    args = parser.parse_args()
    main(args.Path + "/" + args.Name, args.Spotlight, args.Fullscreen)
