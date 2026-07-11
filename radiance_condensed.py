import luxpy as lx
import numpy as np
import pyradiance as pr

def radiance_simulation(source_type='telelumen', ies2rad_input=None, sensor_type='horizontal', eye_h=1.6): 
    # TODO: add options for honeybee + grasshopper
    # TODO: import obj file

    room_l = 1.83
    room_w = 2.43
    room_h = 2.74
    desk_l = 1.22
    desk_w = 0.61
    desk_h = 0.76

    scene_text = f"""
    # materials

    # walls + ceiling 
    void plastic white_wall
    0
    0
    5 0.8 0.8 0.8 0.01 0.01

    # floor
    void plastic carpet_floor
    0
    0
    5 0.2 0.2 0.2 0.01 0.01

    # wood desk
    void plastic wood_desk
    0
    0
    5 0.4 0.3 0.2 0.05 0.1

    # room
    !genbox white_wall room {room_l} {room_w} {room_h} -i

    # desk
    !genbox wood_desk desk_surface {desk_l} {desk_w} {desk_h} | xform -t {(room_l - desk_l) / 2} {(room_w - desk_w) / 2} 0
    """
    # write the scene file
    with open("room.rad", "w") as f:
        f.write(scene_text)

    # import the ies file 
    if source_type == "telelumen":
        ies_file_name = "telelumen octa ies file 22dec18.ies"
    elif source_type == "rubik":
        ies_file_name = "RUBIK_9CS_90CRI_35K_STWH_440LM.ies"
    # elif source_type == "white":
    #     ies_file_name = "white.ies"
    else:
        raise ValueError(f"Source type {source_type} not recognized. Please choose from: telelumen, rubik.")
    
    pr.ies2rad(ies_file_name, outname="light_source")

    # center of the ceiling
    center_x = room_l / 2
    center_y = room_w / 2
    z_height = room_h - 0.05 # Mounted flush/slightly dropped from ceiling

    # spacing between cells (8 inches = ~0.2 meters)
    spacing = 0.2 

    # light placement string 
    if source_type == "telelumen" or source_type == "white":
        # place in center of ceiling, no duplicates
        light_placement = "# Light Fixture\n"
        light_placement += f"!xform -t {center_x:.3f} {center_y:.3f} {z_height} light_source.rad\n"

    elif source_type == "rubik": # place nine cells
        light_placement = "# 9-Cell Rubik Fixture (2x2 ft)\n"

        # Loop through X offsets (-0.2, 0, 0.2)
        for dx in [-spacing, 0, spacing]:
            # Loop through Y offsets (-0.2, 0, 0.2)
            for dy in [-spacing, 0, spacing]:
                
                # Calculate final coordinates for this specific cell
                cell_x = center_x + dx
                cell_y = center_y + dy
                
                # Append this cell to the Radiance file text
                light_placement += f"!xform -t {cell_x:.3f} {cell_y:.3f} {z_height} light_source.rad\n"
    else:
        raise ValueError(f"Source type {source_type} not recognized. Please choose from: telelumen, rubik, white.")

    # write the light placement file
    with open("luminaires.rad", "w") as f:
        f.write(light_placement)

    # compile octree
    octree_bytes = pr.oconv("room.rad", "luminaires.rad")

    # write octree to file
    with open("scene.oct", "wb") as f:
        f.write(octree_bytes)

    # define sensor
    if sensor_type == "horizontal":
        sensor_string = f"{room_l / 2} {room_w / 2} {desk_h} 0 0 1\n"
    elif sensor_type == "vertical":
        sensor_string = f"{room_l / 2} {room_w / 2} {eye_h} 0 1 0\n"
    else:
        raise ValueError(f"Sensor type {sensor_type} not recognized. Please choose from: horizontal, vertical.")
    sensor_point = sensor_string.encode('utf-8')

    # run
    res_bytes = pr.rtrace(
        sensor_point, 
        "scene.oct", 
        header=False, # header=False ensures it only returns the numbers, not the Radiance header text
        params=["-I", "-ab", "5", "-ad", "2048", "-as", "1024", "-h"]    
        )

    # calculate lux
    res_str = res_bytes.decode('utf-8') # turn into python string
    lines = res_str.strip().splitlines() # split the output into lines and remove any leading/trailing whitespace
    data_line = lines[-1] # grab only the very last line (where the RGB data lives)
    r, g, b = map(float, data_line.split()) # split that specific line into the 3 numbers 
    lux = 179 * (0.265 * r + 0.670 * g + 0.065 * b) # calculate illuminance

    print(f"Calculated Illuminance on Desk: {lux:.2f} Lux")

    return lux


# calculate radiance lux, horizontal and vertical
radiance_lux_h = radiance_simulation("telelumen", sensor_type='horizontal') 
radiance_lux_v = radiance_simulation("telelumen", sensor_type='vertical') 
print("Horizontal Illuminance:", radiance_lux_h)
print("Vertical Illuminance:", radiance_lux_v)