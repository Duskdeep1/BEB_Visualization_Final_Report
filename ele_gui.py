# GUI package
import Tkinter as tkinter
from Tkinter import *
#from Tkinter import filedialog
#from Ttkinter import tkMessageBox
import tkFileDialog as filedialog
import tkMessageBox

# Threading
import threading
import time

# calculation package
from ele_bus import *

# FRAME position and size.
FRAME_START_X =                 250
FRAME_START_Y =                 80
FRAME_Width =                   800
FRAME_Height =                  600
thread_init = None
thread_cal = None
thread_bus_type = None

'''
   --------------------------------------
   Action functions.
   --------------------------------------
'''

def _multi_thread_bus_type(output_dir, bus_stops, bus_routes, xlsx_file):
    output_bus_type(output_dir, bus_stops, bus_routes, xlsx_file)

def _multi_thread_cal(glpk_file, bus_stops, bus_routes, xlsx_file, output_dir, bus_num_dict):
    output_result_all(glpk_file = glpk_file, bus_stops = bus_stops, bus_routes = bus_routes, xlsx_file = xlsx_file, output_dir = output_dir, bus_num_dict = bus_num_dict)

def _multi_thread_initiate(bus_stops, bus_routes, xlsx_file):
    eb = EleBus(bus_stops = bus_stops, bus_routes = bus_routes, xlsx_file = xlsx_file)

    eb.cal_distance_for_bus('SATURDAY')
    sat_num = len(eb.filter_by_single_route_length())
    sat_applicable_buses.set(sat_num)

    sat_charge_at_station = len(eb.bus_not_need_charged)
    sat_cant_charge = len(eb.bus_single_route_filtered)
    sat_string = str(sat_num) +  "                   |  " + str(sat_charge_at_station) +  "                                           |  " + str(sat_cant_charge)
    satur_data_num_str.set(sat_string)

    eb = EleBus(bus_stops = bus_stops, bus_routes = bus_routes, xlsx_file = xlsx_file)
    eb.cal_distance_for_bus('SUNDAY')
    sun_num = len(eb.filter_by_single_route_length())
    sun_applicable_buses.set(sun_num)

    sun_charge_at_station = len(eb.bus_not_need_charged)
    sun_cant_charge = len(eb.bus_single_route_filtered)
    sun_string = str(sun_num) +  "                     |  " + str(sun_charge_at_station) +  "                                           |  " + str(sun_cant_charge)
    sun_data_num_str.set(sun_string)

    eb = EleBus(bus_stops = bus_stops, bus_routes = bus_routes, xlsx_file = xlsx_file)
    eb.cal_distance_for_bus('WEEKDAY')
    week_num = len(eb.filter_by_single_route_length())
    #print (week_num)
    week_applicable_buses.set(week_num)

    weekday_charge_at_station = len(eb.bus_not_need_charged)
    weekday_cant_charge = len(eb.bus_single_route_filtered)
    weekday_string = str(week_num) + "                   |  " + str(weekday_charge_at_station) + "                                       |  " + str(weekday_cant_charge)
    weekday_data_num_str.set(weekday_string)


def _check_bus_type_completed():
    if thread_bus_type.is_alive():
        root.after(50, _check_bus_type_completed)
    else:
        bus_type_btn.config(state = "active")
        root.config(cursor = "")
        root.update()
        _display_bus_type_success()

def _check_cal_completed():
    if thread_cal.is_alive():
        root.after(50, _check_cal_completed)
    else:
        calculate_btn.config(state = "active")
        root.config(cursor = "")
        root.update()
        _display_cal_success()

def _check_initiate_completed():
    if thread_init.is_alive():
        root.after(50, _check_initiate_completed)
    else:
        initiate_btn.config(state = "active")
        root.config(cursor = "")
        root.update()
        _display_initiate_success()

def _display_bus_type_success():
    success_msg = StringVar()
    tmplabel =  Label(f, textvariable = success_msg).grid(sticky = 'w', row = 22, column= 1)
    success_msg.set("success...")

def _display_cal_success():
    success_msg = StringVar()
    tmplabel =  Label(f, textvariable = success_msg).grid(sticky = 'w', row = 21, column= 1)
    success_msg.set("success...")

def _display_initiate_success():
    success_msg = StringVar()
    tmplabel =  Label(f, textvariable = success_msg).grid(sticky = 'w', row = 8, column= 1)
    success_msg.set("success...")


    title_label.grid(sticky = 'w', row = 9, column = 0)
    weekday_data_num_label.grid(sticky = 'w', row = 10, column = 0)
    # satur_data_num_label.grid(sticky = 'w', row = 11, column = 0)
    # sun_data_num_label.grid(sticky = 'w', row = 12, column = 0)

    week_buses_label.grid(sticky = 'w', row = 13, column = 0)
    weekday_checkbtn.grid(sticky = 'w', row = 14, column = 0)

    # sat_buses_label.grid(sticky = 'w', row = 15, column = 0)
    # saturday_checkbtn.grid(sticky = 'w', row = 16, column = 0)
    #
    # sun_buses_label.grid(sticky = 'w', row = 17, column = 0)
    # sunday_checkbtn.grid(sticky = 'w', row = 18, column = 0)


    # all_radiobtn.grid(sticky = 'w', row = 11, column = 0)
    # bus_number_radiobtn.grid(sticky = 'w', row = 12, column = 0)

    # bus_number_entry.grid(sticky = 'w', row = 13, column = 0)
    output_dir_label.grid(sticky = 'w', row = 19, column = 0)
    output_dir_btn.grid(sticky = 'w', row = 19, column = 1)
    output_dir_display_label.grid(sticky = 'w', row = 20, column = 0)
    # calculate_btn.grid(sticky = 'w', row = 15 , column = 0)
    # cal_label.grid(sticky = 'w', row = 15, column = 1)

    # bus_type_btn.grid(sticky = 'w', row = 16, column = 0)
    # bus_type_label.grid(sticky = 'w', row = 16, column = 1)


def _action_sat_checkbtn():
    if_checked = value_sat_check.get()
    if if_checked == 1:
        sat_entry.grid(row = 16, column = 1)
    else:
        sat_entry.grid_forget()

def _action_sun_checkbtn():
    if_checked = value_sun_check.get()
    if if_checked == 1:
        sun_entry.grid(row = 18, column = 1)
    else:
        sun_entry.grid_forget()

def _action_week_checkbtn():
    if_checked = value_week_check.get()
    if if_checked == 1:
        week_entry.grid(row = 14, column = 1)
    else:
        week_entry.grid_forget()

def _action_output_dir():
    dir_name = filedialog.askdirectory()
    output_dir_display_str.set(dir_name)

    calculate_btn.grid(sticky = 'w', row = 21 , column = 0)
    cal_label.grid(sticky = 'w', row = 21, column = 1)

    bus_type_btn.grid(sticky = 'w', row = 22, column = 0)
    bus_type_label.grid(sticky = 'w', row = 22, column = 1)


def _action_busStop_shp_input():
    ftypes = [('Shape files', '*.shp'), ('All files', '*')]
    filename = filedialog.askopenfilename(filetypes = ftypes)
    busStop_shp_display_str.set(filename)

def _action_busRoutes_shp_input():
    ftypes = [('Shape files', '*.shp'), ('All files', '*')]
    filename = filedialog.askopenfilename(filetypes = ftypes)
    busRoutes_shp_display_str.set(filename)

def _action_UTARuncut_xls_input():
    ftypes = [('excel file', '*.xlsx'), ('excel file lower version', '*.xls'), ('All files', '*')]
    filename = filedialog.askopenfilename(filetypes = ftypes)
    UTARuncut_xls_display_str.set(filename)

def _action_glpk_input():
    #ftypes = [('All files', '*')]
    filename = filedialog.askopenfilename()
    glpk_display_str.set(filename)

def _action_bus_type():
    output_dir = output_dir_display_str.get()

    bus_stops = busStop_shp_display_str.get()
    bus_routes = busRoutes_shp_display_str.get()
    xlsx_file = UTARuncut_xls_display_str.get()

    #bus_type_str.set("calculating...")
    bus_type_msg = StringVar()
    tmplabel =  Label(f, textvariable = bus_type_msg).grid(sticky = 'w', row = 22 , column= 1)
    bus_type_msg.set("calculating...")

    global thread_bus_type
    thread_bus_type = threading.Thread(target = _multi_thread_bus_type, args = (output_dir, bus_stops, bus_routes, xlsx_file,))

    bus_type_btn.config(state = "disabled")
    root.config(cursor = "wait")
    root.update()

    thread_bus_type.start()
    root.after(50, _check_bus_type_completed)

def _action_initiate():

    bus_stops = busStop_shp_display_str.get()
    bus_routes = busRoutes_shp_display_str.get()
    xlsx_file = UTARuncut_xls_display_str.get()

    initiate_str.set("initiating...")

    # initiate a thread.
    global thread_init
    thread_init = threading.Thread(target = _multi_thread_initiate, args = (bus_stops, bus_routes, xlsx_file,))

    # diable button and change cursor to wait mode.
    initiate_btn.config(state = "disabled")
    root.config(cursor = "wait")
    root.update()

    thread_init.start()
    root.after(50, _check_initiate_completed)

def _action_calculate():

    glpk_file = glpk_display_str.get()
    bus_stops = busStop_shp_display_str.get()
    bus_routes = busRoutes_shp_display_str.get()
    xlsx_file = UTARuncut_xls_display_str.get()
    output_dir = output_dir_display_str.get()


    #cal_str.set("calculating...")
    error_string = ""
    bus_num_dict = {'SUNDAY': 0, 'SATURDAY': 0, 'WEEKDAY': 0}
    if value_sat_check.get() == 1:
        if (sat_num.get() > sat_applicable_buses.get() or sat_num.get() <= 0):
            error_string += "For Saturday, please input a number between 1 and " + str(sat_applicable_buses.get()) + " !\n"
        bus_num_dict['SATURDAY'] = sat_num.get()
    if value_sun_check.get() == 1:
        if (sun_num.get() > sun_applicable_buses.get() or sun_num.get() <= 0):
            error_string += "For Sunday, please input a number between 1 and " + str(sun_applicable_buses.get()) + " !\n"
        bus_num_dict['SUNDAY'] = sun_num.get()
    if value_week_check.get() == 1:
        if (week_num.get() > week_applicable_buses.get() or week_num.get() <= 0):
            error_string += "For Weekday, please input a number between 1 and " + str(week_applicable_buses.get()) + " !\n"
        bus_num_dict['WEEKDAY'] = week_num.get()

    if len(error_string)!=0:

        return
    cal_msg = StringVar()
    tmplabel =  Label(f, textvariable = cal_msg).grid(sticky = 'w', row = 21, column= 1)
    cal_msg.set("calculating...")
    #print (bus_num_dict)

    global thread_cal
    thread_cal = threading.Thread(target = _multi_thread_cal, args = (glpk_file, bus_stops, bus_routes, xlsx_file, output_dir, bus_num_dict))

    calculate_btn.config(state = "disabled")
    root.config(cursor = "wait")
    root.update()

    thread_cal.start()
    root.after(50, _check_cal_completed)

root = Tk()
root.title("Ele Bus Replace Analysis")
root.geometry(str(FRAME_Width) + "x" + str(FRAME_Height) + "+" + str(FRAME_START_X) + "+" + str(FRAME_START_Y))
root.configure(background = 'White')
f = Frame(root)
f.grid(row=0,column=0)
#place buttons on the *frame*

'''
   --------------------------------------
   Bus stop shapefile handling.
   --------------------------------------
'''

busStop_shp_input_label = Label(f, text = 'Please choose the bus stop input shape file').grid(sticky = 'w', row = 0, column = 0)
busStop_shp_input_btn = Button(f, text = 'Browser', command = _action_busStop_shp_input)
busStop_shp_input_btn.grid(sticky = 'w', row = 0, column = 1)

busStop_shp_display_str = StringVar()
busStop_shp_display_label = Label(f, textvariable = busStop_shp_display_str).grid(sticky = 'w', row = 1, column = 0)

'''
  ----------------------------------------
   Bus routes shapefile handling.
  ----------------------------------------
'''

busRoutes_shp_input_label = Label(f, text = 'Please choose the bus route input shape file').grid(sticky = 'w', row = 2, column = 0)
busRoutes_shp_input_btn = Button(f, text = 'Browser', command = _action_busRoutes_shp_input)
busRoutes_shp_input_btn.grid(sticky = 'w', row = 2, column = 1)

busRoutes_shp_display_str = StringVar()
busRoutes_shp_display_label = Label(f, textvariable = busRoutes_shp_display_str).grid(sticky = 'w', row = 3, column = 0)

'''
  ----------------------------------------
   UTA Runcut xlsx file handling.
  ----------------------------------------
'''

UTARuncut_xls_input_label = Label(f, text = 'Please choose the Transit runcut xlsx file').grid(sticky = 'w', row = 4, column = 0)
UTARuncut_xls_input_btn = Button(f, text = 'Browser', command = _action_UTARuncut_xls_input)
UTARuncut_xls_input_btn.grid(sticky = 'w', row = 4, column = 1)

UTARuncut_xls_display_str = StringVar()
UTARuncut_xls_display_label = Label(f, textvariable = UTARuncut_xls_display_str).grid(sticky = 'w', row = 5, column = 0)

'''
  ----------------------------------------
   glpk file handling.
  ----------------------------------------
'''

glpk_input_label = Label(f, text = 'Please choose the glpk file').grid(sticky = 'w', row = 6, column = 0)
glpk_input_btn = Button(f, text = 'Browser', command = _action_glpk_input)
glpk_input_btn.grid(sticky = 'w', row = 6, column = 1)

glpk_display_str = StringVar()
glpk_display_label = Label(f, textvariable = glpk_display_str).grid(sticky = 'w', row = 7, column = 0)

'''
  ----------------------------------------
  initiation.
  ----------------------------------------
'''
initiate_btn = Button(f, text = 'Initiate', command = _action_initiate)
initiate_btn.grid(sticky = 'w', row = 8, column = 0)

initiate_str = StringVar()
initiate_label = Label(f, textvariable = initiate_str).grid(sticky = 'w', row = 8, column= 1)

'''
  ----------------------------------------
  Buses table
  ----------------------------------------
'''

title_label = Label(f, text = "Applicable bus | No needed charge in routes | Can't charged in routes")

weekday_label = Label(f, text = "Weekday")
saturday_label = Label(f, text = "Saturday")
sunday_label = Label(f, text = "Sunday")

weekday_data_num_str = StringVar()
weekday_data_num_label = Label(f, textvariable = weekday_data_num_str)
#
satur_data_num_str = StringVar()
# satur_data_num_label = Label(f, textvariable = satur_data_num_str)
#
sun_data_num_str = StringVar()
# sun_data_num_label = Label(f, textvariable = sun_data_num_str)


'''
  ----------------------------------------
  bus_type
  ----------------------------------------

'''

bus_type_btn = Button(f, text = 'output bus types xlsx', command = _action_bus_type)
bus_type_str = StringVar()
bus_type_label = Label(f, textvariable = bus_type_str)

'''
  ----------------------------------------
  SAT, SUN, WEEK day check buttons.
  ----------------------------------------
'''

value_sat_check = IntVar()
value_sun_check = IntVar()
value_week_check = IntVar()

# saturday_checkbtn = Checkbutton(f, text="SATURDAY", variable=value_sat_check, command = _action_sat_checkbtn)
# sunday_checkbtn = Checkbutton(f, text="SUNDAY", variable=value_sun_check, command = _action_sun_checkbtn)
weekday_checkbtn = Checkbutton(f, text="Budget", variable=value_week_check, command = _action_week_checkbtn) #Biao

sat_applicable_buses = IntVar()
sat_buses_label = Label(f, textvariable = sat_applicable_buses)

sun_applicable_buses = IntVar()
sun_buses_label = Label(f, textvariable = sun_applicable_buses)

week_applicable_buses = IntVar()
week_buses_label = Label(f, textvariable = week_applicable_buses)

sat_num = IntVar()
# sat_entry = Entry(f, textvariable = sat_num)
#
sun_num = IntVar()
# sun_entry = Entry(f, textvariable = sun_num)

week_num = IntVar()
week_entry = Entry(f, textvariable = week_num)

'''
  ----------------------------------------
  All, or chosen bus number.
  ----------------------------------------
'''

value_radiobtn = IntVar()
all_radiobtn = Radiobutton(f, text="All", variable=value_radiobtn, value = 1)
bus_number_radiobtn = Radiobutton(f, text="Number of bus", variable=value_radiobtn, value = 2)

bus_number_content = StringVar()
bus_number_entry = Entry(f, textvariable = bus_number_content)


'''
  ----------------------------------------
  Choose directory widgets.
  ----------------------------------------
'''

output_dir_label = Label(f, text = 'Please choose the output directory:')
output_dir_btn = Button(f, text = 'Browser', command = _action_output_dir)
output_dir_display_str = StringVar()
output_dir_display_label = Label(f, textvariable = output_dir_display_str)

calculate_btn = Button(f, text = 'Calculate', command = _action_calculate)
cal_str = StringVar()
cal_label = Label(f, textvariable = cal_str)

'''
   Main loop.
'''
root.mainloop()