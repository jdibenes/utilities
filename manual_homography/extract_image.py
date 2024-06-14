
import os
import cv2
import numpy as np
import base64
import csv

path_data = './data'
path_save = './save'
video_formats = {'.avi', '.mp4'}
image_formats = {'.png'}
resize_height = 540

def collect_files_by_format(path_data, formats):
    return [f for f in os.listdir(path_data) if os.path.isfile(os.path.join(path_data, f)) and os.path.splitext(f)[1].lower() in formats]

def collect_images(frames, file, image, resize_height):
    resize_factor = resize_height / image.shape[0]
    frames[file] = cv2.resize(image, None, fx=resize_factor, fy=resize_factor)
    return frames

def match_image_pair(frames, key_1, key_2, path_save):
    def on_mouse(event, x, y, flags, param):
        fb = param['stacked'].copy()
        state = param['state']
        select_1 = param['select_1']
        select_2 = param['select_2']
        x_2 = param['x_2']
        matches = param['matches']
        points_1 = param['points_1']
        points_2 = param['points_2']
        edit_target = param['edit_target']

        if (event == cv2.EVENT_MOUSEMOVE): # update
            if (state == 2): # update match
                match = edit_target['match']
                matches[edit_target['key_m']] = [x, y, match[2], match[3]] if (edit_target['side_1']) else [match[0], match[1], x, y]
        elif (event == cv2.EVENT_LBUTTONDOWN): # begin / edit / end
            targets = []

            for v in range(y-2, y+3):
                for u in range(x-2, x+3):
                    key_x = f'{u},{v}'
                    side_1 = x < x_2
                    key_m = points_1.get(key_x, None) if (side_1) else points_2.get(key_x, None)
                    if (key_m):
                        targets.append({'side_1' : side_1, 'distance' : max(abs(x - u), abs(y - v)), 'key_m' : key_m, 'match' : matches[key_m]})

            if (state == 0): # begin / edit
                if (len(targets) == 0): # begin match
                    select_1 = (x, y)
                    state = 1
                else: # edit match
                    targets.sort(key = lambda t : t['distance'])
                    if ((len(targets) == 1) or (targets[0]['distance'] < targets[1]['distance'])):
                        edit_target = targets[0]
                        key_1, key_2 = edit_target['key_m'].split('|')
                        points_1.pop(key_1)
                        points_2.pop(key_2)
                        state = 2
            elif (state == 1): # end match
                if (len(targets) == 0):
                    select_2 = (x, y)
                    if (select_1[0] > select_2[0]):
                        s_1, s_2 = (select_2, select_1)
                    else:
                        s_1, s_2 = (select_1, select_2)
                    if ((s_1[0] < x_2) and (s_2[0] >= x_2)):
                        match = [s_1[0], s_1[1], s_2[0], s_2[1]]
                        key_m = f'{match[0]},{match[1]}|{match[2]},{match[3]}'
                        key_1, key_2 = key_m.split('|')
                        matches[key_m] = match
                        points_1[key_1] = key_m
                        points_2[key_2] = key_m
                        state = 0
            elif (state == 2): # confirm match
                if (len(targets) == 0):
                    side_1 = edit_target['side_1']
                    if (side_1 == (x < x_2)):
                        matches.pop(edit_target['key_m'])
                        old = edit_target['match']
                        match = [x, y, old[2], old[3]] if (side_1) else [old[0], old[1], x, y]
                        key_m = f'{match[0]},{match[1]}|{match[2]},{match[3]}'
                        key_1, key_2 = key_m.split('|')
                        matches[key_m] = match
                        points_1[key_1] = key_m
                        points_2[key_2] = key_m
                        state = 0
        elif (event == cv2.EVENT_RBUTTONDOWN): # erase / cancel
            if (state == 0): # erase match
                for v in range(y-2, y+3):
                    for u in range(x-2, x+3):
                        key_x = f'{u},{v}'
                        key_m = points_1.get(key_x, None) if (u < x_2) else points_2.get(key_x, None)
                        if (key_m):
                            key_1, key_2 = key_m.split('|')
                            matches.pop(key_m)                            
                            points_1.pop(key_1)
                            points_2.pop(key_2)
            elif (state == 1): # cancel match
                state = 0
            elif (state == 2): # cancel edit
                key_m = edit_target['key_m']
                key_1, key_2 = key_m.split('|')
                matches[key_m] = edit_target['match']
                points_1[key_1] = key_m
                points_2[key_2] = key_m
                state = 0

        param['state'] = state
        param['select_1'] = select_1
        param['select_2'] = select_2
        param['edit_target'] = edit_target

        for match in matches.values():
            cv2.rectangle(fb, (match[0] - 1, match[1] - 1), (match[0] + 1, match[1] + 1), (0, 128, 255), 1)
            cv2.rectangle(fb, (match[2] - 1, match[3] - 1), (match[2] + 1, match[3] + 1), (0, 128, 255), 1)
            cv2.line(fb, (match[0], match[1]), (match[2], match[3]), (0, 128, 255), 1)
        if (state == 1):
            cv2.rectangle(fb, (select_1[0] - 1, select_1[1] - 1), (select_1[0] + 1, select_1[1] + 1), (255, 0, 255), 1)
            cv2.line(fb, select_1, (x, y), (255, 0, 255), 1)

        cv2.rectangle(fb, (x - 2, y - 2), (x + 2, y + 2), (0, 255, 0), 1)

        cv2.imshow('stacked', fb)

    keys = [key_1, key_2]
    keys.sort()
    filename = os.path.join(path_save, f'{keys[0]}{keys[1]}.csv')

    image_1 = frames[key_1]
    image_2 = frames[key_2]

    stacked = np.hstack((image_1, image_2))

    param = {}
    param['stacked'] = stacked
    param['state'] = 0
    param['select_1'] = (0, 0)
    param['select_2'] = (0, 0)
    param['x_2'] = image_1.shape[1]
    param['matches'] = {}
    param['points_1'] = {}
    param['points_2'] = {}
    param['edit_target'] = {}
    
    cv2.imshow('stacked', stacked)
    cv2.setMouseCallback('stacked', on_mouse, param)

    while (True):
        key = cv2.waitKey(0)
        if (key == 0x1B): # esc - done
            break
        elif (key == 112): # p - clear
            param['matches'] = {}
            print('Cleared canvas')
        elif (key == 115): # s - save
            with open(filename, 'w', newline='') as file:
                csv.writer(file).writerows(list(param['matches'].values()))
            print(f'Saved {filename}')
        elif (key == 114): # r - load
            with open(filename, 'r') as file:
                param['matches'] = {f'{line[0]},{line[1]}|{line[2]},{line[3]}' : [int(line[0]), int(line[1]), int(line[2]), int(line[3])] for line in csv.reader(file)}
            for key_m in param['matches'].keys():
                k_1, k_2 = key_m.split('|')
                param['points_1'][k_1] = key_m
                param['points_2'][k_2] = key_m
            print(f'Loaded {filename}')
        elif (key == 0x20): # space - find homography
            p1 = []
            p2 = []
            for match in param['matches'].values():
                p1.append([match[0], match[1]])
                p2.append([match[2] - param['x_2'], match[3]])
            if (len(p1) < 4):
                print('NOT ENOUGHT POINTS!')
                continue
            p1 = np.array(p1)
            p2 = np.array(p2)
            h, status = cv2.findHomography(p1, p2)

            corners = h @ np.array([[0, 0, 1], [0, image_1.shape[0], 1], [image_1.shape[1], 0, 1], [image_1.shape[1], image_1.shape[0], 1]]).T
            corners = corners / corners[2, :]
            print(corners)

            htest = image_2.copy()
            cv2.line(htest, (int(corners[0,0]), int(corners[1,0])), (int(corners[0,1]), int(corners[1,1])), (0, 255, 0), 1)
            cv2.line(htest, (int(corners[0,0]), int(corners[1,0])), (int(corners[0,2]), int(corners[1,2])), (0, 255, 0), 1)
            cv2.line(htest, (int(corners[0,3]), int(corners[1,3])), (int(corners[0,1]), int(corners[1,1])), (0, 255, 0), 1)
            cv2.line(htest, (int(corners[0,3]), int(corners[1,3])), (int(corners[0,2]), int(corners[1,2])), (0, 255, 0), 1)
            cv2.imshow('HTST', htest)





            print('Homography results')
            print(h)
            print(status)
            #im_dst = cv2.warpPerspective(image_1, h, image_2.shape[0:2])
            #cv2.imshow('HTEST',im_dst)

        on_mouse(-1, -1, -1, -1, param)

    cv2.destroyWindow('stacked')

    return param['matches']

video_files = collect_files_by_format(path_data, video_formats)
image_files = collect_files_by_format(path_data, image_formats)

frames = {}

for file in video_files:
    capture = cv2.VideoCapture(os.path.join(path_data, file))
    collect_images(frames, file, capture.read()[1], resize_height)
    capture.release()

for file in image_files:
    collect_images(frames, file, cv2.imread(os.path.join(path_data, file)), resize_height)

frame_keys = list(frames.keys())

for index, key in enumerate(frame_keys):
    print(f'[{index}]: "{key}"')

selection = input("indices: ")
indices = [int(index.strip()) for index in selection.split(',')]

matches = match_image_pair(frames, frame_keys[indices[0]], frame_keys[indices[1]], path_save)

print(matches)
