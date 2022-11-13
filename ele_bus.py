from fileHandler import _parseXLSX, FileReader
from datetime import time
import shapefile
import xlwt
import os,platform
import ele_glpk_solve as op
import pandas as pd

FILENAME = r"../input/UTA Runcut File  Aug2016.xlsx"

FILEDNAME =  ['LineAbbr', 'ServiceName', 'DirectionName', 'block_num', 'trip_id', 'from_stop', 'FromTime', 'to_stop', 'ToTime', 'TimeRange', 'Length']

STOP_FIELDNAME = ['InService', 'OnStreet', 'Shelter', 'AtStreet', 'LocationUs', 'StopName', 'Garbage', 'Lighting', 'UTAStopID', 'Bicycle', 'Transfer', 'StopId', 'City', 'StreetNum', 'Bench', 'StationId']#, 'sequenceId', 'z', 'isCharging']

# New added, bus running time type.
BUS_RUNINING_TIME_TYPE = ['WEEKDAY', 'SATURDAY', 'SUNDAY']
#BUS_RUNINING_TIME_TYPE = ['WEEKDAY']

SHEET_NAME = "Aug2016"

METER_TO_MILE = 0.000621371192

TIMEGAP = 10

sys_windows = "Windows"

class EleBus:
    def __init__(self, bus_stops, bus_routes, xlsx_file):

        if(platform.system() == sys_windows):
            bus_stops = bus_stops.replace("/", "\\")
            bus_routes = bus_routes.replace("/", "\\")
            xlsx_file = xlsx_file.replace("/", "\\")

        self.shpfile_reader = FileReader(busStops = bus_stops , busRoutes = bus_routes)
        global FILENAME
        FILENAME = xlsx_file
        print FILENAME
        self.shpfile_reader.initData()

        self.xlsx_info = []

        self.bus_num = set()

        self.bus_stops = []

        self.potential_bus_stops = []

        self.potential_bus_sets = dict()

        self.bus_stop_maps = dict()

        self.ik_list = []

        self.shp_writer = shapefile.Writer(shapefile.POLYLINEZ)


        # bus types

        self.bus_not_need_charged = []

        self.bus_single_route_filtered = []

        self.cant_charged = []

        self.less_than_251 = []

        # 3D shapefile

        # mapList busId_sequenceId, stop_name, time
        self.sequenceTimeList = dict()

        self.stop_sequnceTimeList = dict()

    def read_Runcut_xlsx(self, run_time_type, col_id=0, sheet_name=SHEET_NAME):

        print FILENAME
        wb = _parseXLSX(FILENAME)
        table = wb.sheet_by_name(sheet_name)
        colnames =  table.row_values(col_id)
        list = []
        for rownum in range(1,table.nrows):
            row = table.row_values(rownum)
            if row:
                app = {}
                if row[1] != run_time_type:
                    continue
                for i in range(len(colnames)):
                    if colnames[i] == 'FromTime' or colnames[i] == 'ToTime':
                        x = int(row[i] * 24 * 3600) # convert to number of seconds
                        hour = x//3600
                        minute = (x%3600)//60
                        if x%60 == 59:
                            minute +=1
                        if hour >= 24:
                            hour = hour%24
                        realtime = time(hour, minute)
                        app['R_'+colnames[i]] = realtime
                    app[colnames[i]] = row[i]
                list.append(app)
        #print ("runcut size", len(list), ' ', table.nrows)
        return list

    def read_routes(self):
        bus_routes_dicts = self.shpfile_reader.busRoutesRecordDicts

        return bus_routes_dicts

    def cal_distance_for_bus(self, run_time_type = 'WEEKDAY'):

        self.xlsx_info = self.read_Runcut_xlsx(run_time_type)
        #print (self.xlsx_info)
        routes_info = self.read_routes()

        for xlsx_item in self.xlsx_info:
            if xlsx_item['from_stop'] not in self.bus_stops:
                self.bus_stops.append(xlsx_item['from_stop'])
            if xlsx_item['to_stop'] not in self.bus_stops:
                self.bus_stops.append(xlsx_item['to_stop'])

            self.bus_num.add(xlsx_item['block_num'])
            xlsx_item["Length"] = 0.0
            time_range =  (xlsx_item["ToTime"] * 24 * 3600 - xlsx_item["FromTime"]*24*3600)/60

            xlsx_item['TimeRange'] = time_range

            for routes_item in routes_info:
                if xlsx_item["LineAbbr"] == routes_item["LineAbbr"]:
                    xlsx_item["Length"] = float(routes_item["Shape_Leng"])*METER_TO_MILE

        #self.write_xls(self.xlsx_info)
        #self.matchStops()
    def sum_timeAndLength(self):

        resultList = []

        for v in self.bus_num:
            total_time = 0
            total_length = 0.0
            for item in self.xlsx_info:
                if item['block_num'] == v:
                    total_time += item['TimeRange']
                    total_length += item['Length']

            resultList.append({'block_num': v, 'total_time': round(total_time), 'total_length': round(total_length, 2)})

        return resultList

    def output_sum(self):

        resultList = self.sum_timeAndLength()
        resultList = sorted(resultList, key=lambda result: result['block_num'])
        self.write_xls(resultList, ['block_num', 'total_time', 'total_length'], '../output/UTA_Runcut_sum_output', sheetName = 'Aug2016')

    def output_info(self):
        self.write_xls(self.xlsx_info)

    def filter_by_length(self, max_length = 62.0, max_length_2 = 251.0):

        resultList = self.sum_timeAndLength()
        filterList = []
        for item in resultList:
            if item['total_length'] > max_length and item['total_length'] <= max_length_2:
                filterList.append(item)
                self.less_than_251.append(item)
            elif item['total_length'] <= max_length:
                self.bus_not_need_charged.append(item)
                self.less_than_251.append(item)
            elif item['total_length'] > max_length_2:
                filterList.append(item)
                self.cant_charged.append(item)

        #print ("<62:",len(self.bus_not_need_charged))
        #self.write_xls(filterList,  ['block_num', 'total_time', 'total_length'], '../output/UTA_Runcut_bus_len_less_than_range', sheetName = 'Aug2016')
        return filterList

    def filter_by_single_route_length(self, max_length = 62.0):

        filterList = self.filter_by_length()

        filterSet = set()
        single_route_filter_list = []
        for item in self.xlsx_info:
            if item['Length'] > max_length:
                filterSet.add(item['block_num'])
                single_route_filter_list.append(item)

        applicable_bus_set = set()
        new_filterList = []
        no_applicable_list = []
        no_applicable_set = set()
        for item in filterList:
            if item['block_num'] not in filterSet:
                applicable_bus_set.add(item['block_num'])
                new_filterList.append(item)
            elif item['block_num'] not in no_applicable_set:
                no_applicable_set.add(item['block_num'])
                no_applicable_list.append(item)

        self.bus_single_route_filtered = no_applicable_list

        #print ("single_route:",len(self.bus_single_route_filtered))
        filter_xlsx_info = []
        filter_bus_set = set()
        for xlsx_item in self.xlsx_info:
            if xlsx_item['block_num'] in applicable_bus_set:
                filter_xlsx_info.append(xlsx_item)
                filter_bus_set.add(xlsx_item['block_num'])


        # create filter xlsx_info filtered by bus route length
        self.bus_num = filter_bus_set
        self.xlsx_info = filter_xlsx_info

        # self.write_xls(new_filterList,  ['block_num', 'total_time', 'total_length'], '../output/UTA_Runcut_Applicable_bus_update', sheetName = 'Aug2016')
        # self.write_xls(no_applicable_list,  ['block_num', 'total_time', 'total_length'], '../output/UTA_Runcut_not_applicable_bus_by_single_route', sheetName = 'Aug2016')
        return new_filterList

    def filter_bus_by_time(self):

        ik_list = self.ik_list

        bus_list = self.filter_by_single_route_length()

        count_bus_stops_num = dict()
        for item in ik_list:
            block_num = str(int(item['block_num']))

            if block_num not in count_bus_stops_num.keys():
                count_bus_stops_num[block_num] = 0
            else:
                if item['time_gap'] >= TIMEGAP:
                    count_bus_stops_num[block_num] = 1

        unfeasible_bus_list = []
        for k,v in count_bus_stops_num.items():
            if v == 0:
                unfeasible_bus_list.append(k)

        return unfeasible_bus_list

    def write_xls(self, resultList,
                fieldnames = FILEDNAME,
                fileName = '../output/UTA_Runcut_output',
                sheetName = 'Aug2016'):

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet(sheetName)

        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'h:mm'

        for i,v in enumerate(fieldnames):
            worksheet.write(0,i,v)

        for i in range(1,len(resultList)):
            for j,v in enumerate(fieldnames):
                if v == 'ToTime' or v == 'FromTime':
                    worksheet.write(i, j, resultList[i-1]['R_'+v], date_format)
                elif v == 'Length' or v == 'total_length':
                    worksheet.write(i, j, str(resultList[i-1][v]))
                else:
                    worksheet.write(i, j, resultList[i-1][v])

        workbook.save(fileName+'.xls')

    def write_xls_multi_sheets(self, resultLists,
                fieldnames = ['block_num', 'total_time', 'total_length'],
                fileName = '../output/UTA_Runcut_bus_type',
                               sheetNames = ['applicable','single_route_not_applicable', 'less_than_62', 'less_than_251', 'larger_than_251']):

        workbook = xlwt.Workbook()

        # wrtie multiple sheets
        for sheetCount, sheetName in enumerate(sheetNames):
            worksheet = workbook.add_sheet(sheetName)

            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'h:mm'

            for i,v in enumerate(fieldnames):
                worksheet.write(0,i,v)

            for i in range(1,len(resultLists[sheetCount])+1):
                for j,v in enumerate(fieldnames):
                    if v == 'ToTime' or v == 'FromTime':
                        worksheet.write(i, j, resultList[sheetCount][i-1]['R_'+v], date_format)
                    elif v == 'Length' or v == 'total_length':
                        worksheet.write(i, j, str(resultLists[sheetCount][i-1][v]))
                    else:
                        worksheet.write(i, j, resultLists[sheetCount][i-1][v])

        workbook.save(fileName+'.xls')

    def write_station_2D_shp(self, resultList, fileName, field = STOP_FIELDNAME):

        self.shp_writer = shapefile.Writer(shapefile.POINT)

        for f in field:
            self.shp_writer.field(f, 'C', '60')

        for item in self.potential_bus_stops:
            #print(item)

            # for sequence_item in self.stop_sequnceTimeList[item['stop_name']]:

            #     isCharging = 1
            #     if sequence_item['sequenceId'] not in resultList:
            #         continue
            #         print ('coming!!!', sequence_item['sequenceId'])
            #         isCharging = 1

            stop_name = item['stop_name'].strip()
            if stop_name not in self.bus_stop_maps.keys():
                continue

                #print ((sequence_item['time'].hour*60 + sequence_item['time'].minute)*10)
            point = self.bus_stop_maps[stop_name]['point']

                # print ('station: ', [point[0][0], point[0][1], (sequence_item['time'].hour*60 + sequence_item['time'].minute)*100, 0])

            self.shp_writer.point(point[0][0], point[0][1])

                #print (self.shp_writer.shapes()[0].points)
            tmp_set = self.bus_stop_maps[stop_name]

                #print (tmp_set)
            self.shp_writer.record(tmp_set[field[0]], tmp_set[field[1]], tmp_set[field[2]], tmp_set[field[3]], tmp_set[field[4]], tmp_set[field[5]], tmp_set[field[6]], tmp_set[field[7]], tmp_set[field[8]], tmp_set[field[9]], tmp_set[field[10]], tmp_set[field[11]], tmp_set[field[12]], tmp_set[field[13]], tmp_set[field[14]], item['stop_id'])


        self.shp_writer.save(fileName)
        print ('stops write succeed')


    def write_result_shp(self, resultList, fileName, field = STOP_FIELDNAME):

        self.shp_writer = shapefile.Writer(shapefile.POINTZ)

        for f in field:
            self.shp_writer.field(f, 'C', '60')

        for item in self.potential_bus_stops:
            #print(item)

            for sequence_item in self.stop_sequnceTimeList[item['stop_name']]:

                isCharging = 1
                if sequence_item['sequenceId'] not in resultList:
                    continue
                    #print ('coming!!!', sequence_item['sequenceId'])
                    isCharging = 1

                stop_name = item['stop_name'].strip()
                if stop_name not in self.bus_stop_maps.keys():
                    continue

                #print ((sequence_item['time'].hour*60 + sequence_item['time'].minute)*10)
                point = self.bus_stop_maps[stop_name]['point']

                # print ('station: ', [point[0][0], point[0][1], (sequence_item['time'].hour*60 + sequence_item['time'].minute)*100, 0])

                self.shp_writer.point(point[0][0], point[0][1], (sequence_item['time'].hour*60 + sequence_item['time'].minute)*100, 0)

                #print (self.shp_writer.shapes()[0].points)
                tmp_set = self.bus_stop_maps[stop_name]

                #print (tmp_set)
                self.shp_writer.record(tmp_set[field[0]], tmp_set[field[1]], tmp_set[field[2]], tmp_set[field[3]], tmp_set[field[4]], tmp_set[field[5]], tmp_set[field[6]], tmp_set[field[7]], tmp_set[field[8]], tmp_set[field[9]], tmp_set[field[10]], tmp_set[field[11]], tmp_set[field[12]], tmp_set[field[13]], tmp_set[field[14]], item['stop_id'], sequence_item['sequenceId'], (sequence_item['time'].hour*60 + sequence_item['time'].minute)*100, isCharging)


        self.shp_writer.save(fileName)
        print ('stops write succeed')

        '''
        bus line shp file.

        '''
    def write_bus_line_shp(self, filter_set, fileName, field = FILEDNAME):

        self.shp_writer = shapefile.Writer(shapefile.POLYLINEZ)
        for f in field:
            self.shp_writer.field(f, 'C', '60')


        for v in self.xlsx_info:

            # if v['from_stop_point'] == [0,0]:
            #     print (v['from_stop'])
            # if v['to_stop_point'] == [0,0]:
            #     print (v['to_stop'])

            if int(v['block_num']) not in filter_set:
                continue

            if v['from_stop_point'] == [0,0] or v['to_stop_point'] == [0,0]:
                continue


            #print ('---------survive-------')
            from_stop_z = (v['R_FromTime'].hour*60 + v['R_FromTime'].minute)*100
            to_stop_z = (v['R_ToTime'].hour*60 + v['R_ToTime'].minute)*100

            # if from_stop_z < 1:
            #     print (from_stop_z)

            # if to_stop_z < 1:
            #     print (from_stop_z)

            from_stop_coord = v['from_stop_point'][0]
            from_stop_coord = [from_stop_coord[0], from_stop_coord[1], from_stop_z, 0]

            to_stop_coord = v['to_stop_point'][0]
            to_stop_coord = [to_stop_coord[0], to_stop_coord[1], to_stop_z, 0]

            #print (from_stop_coord)
            #print (to_stop_coord)
            self.shp_writer.line(parts = [[from_stop_coord, to_stop_coord]])
            self.shp_writer.record(v['LineAbbr'], v['ServiceName'], v['DirectionName'], v['block_num'], v['trip_id'], v['from_stop'], v['R_FromTime'], v['to_stop'], v['R_ToTime'], int(v['TimeRange']), v['Length'])

#        print (self.xlsx_info)
        self.shp_writer.save(fileName)
        print ('write succeed!')

    def write_bus_line_adj_shp(self, filter_set, fileName, field = FILEDNAME):

        self.shp_writer = shapefile.Writer(shapefile.POLYLINEZ)
        for f in field:
            self.shp_writer.field(f, 'C', '60')


        bus_line_adj_dict = dict()
        for v in self.xlsx_info:
            # if v['from_stop_point'] == [0,0]:
            #     print (v['from_stop'])
            # if v['to_stop_point'] == [0,0]:
            #     print (v['to_stop'])
            if int(v['block_num']) not in filter_set:
                continue

            if v['from_stop_point'] == [0,0] or v['to_stop_point'] == [0,0]:
                continue

            #print (v)

            #print ('---------survive-------')
            from_stop_z = (v['R_FromTime'].hour*60 + v['R_FromTime'].minute)*100
            to_stop_z = (v['R_ToTime'].hour*60 + v['R_ToTime'].minute)*100

            from_stop_coord = v['from_stop_point'][0]
            from_stop_coord = [from_stop_coord[0], from_stop_coord[1], from_stop_z, 0]

            to_stop_coord = v['to_stop_point'][0]
            to_stop_coord = [to_stop_coord[0], to_stop_coord[1], to_stop_z, 0]


            if v['block_num'] not in bus_line_adj_dict.keys():
                bus_line_adj_dict[v['block_num']] = []

            bus_line_adj_dict[v['block_num']].append(from_stop_coord)
            bus_line_adj_dict[v['block_num']].append(to_stop_coord)

        for k,v in bus_line_adj_dict.items():
            self.shp_writer.line(parts = [v])
            self.shp_writer.record(k)

            # self.shp_writer.line(parts = [[from_stop_coord, to_stop_coord]])
            # self.shp_writer.record(v['LineAbbr'], v['ServiceName'], v['DirectionName'], v['block_num'], v['trip_id'], v['from_stop'], v['R_FromTime'], v['to_stop'], v['R_ToTime'], int(v['TimeRange']), v['Length'])

#        print (self.xlsx_info)
        self.shp_writer.save(fileName)
        print ('write succeed!')

        # self.shp_writer.save('../output/UTA_Runcut_shp_output')
        # print 'write succeed!'


    def matchStops(self):
        bus_stops = self.shpfile_reader.getBusStopsRecords()
        bus_stops_records_dict = self.shpfile_reader.busStopsRecordDicts

        for i,v in enumerate(bus_stops_records_dict):
            stop_name = v['StopName']

            if v['UTAStopID'] == '182025':
                #print (v)
                continue

            if stop_name == 'COUNTRY HILLS DR @ 1170 E (FLYNG J)':
                stop_name = 'COUNTRY HILLS DR @ 1170 E (FLYNG J'


            v['point'] = bus_stops[i].shape.points

            self.bus_stop_maps[stop_name] = v

        #print (self.bus_stop_maps['400 S @ 198 W'])
        #print (self.bus_stop_maps['9000 S @ 3690 W'].keys())
        # for v in bus_stops_records_dict:
        #     print (v['StopName'])

        # for v in bus_stops_records_dict:
        #     print v['StopName']

        for xlsx_item in self.xlsx_info:

            from_stop = xlsx_item['from_stop'].strip()
            to_stop = xlsx_item['to_stop'].strip()

            xlsx_item['from_stop_point'] = [0,0]
            xlsx_item['to_stop_point'] = [0,0]
            for i,v in enumerate(bus_stops_records_dict):
                if v['UTAStopID'] == '182025':
                    continue
                if to_stop == 'COUNTRY HILLS DR @ 1170 E (FLYNG J':
                    to_stop = to_stop+')'
                if from_stop == v['StopName']:
                    xlsx_item['from_stop_point'] = bus_stops[i].shape.points
                if to_stop == v['StopName']:
                    xlsx_item['to_stop_point'] = bus_stops[i].shape.points

    def generate_potential_station(self, minGap = TIMEGAP):

        potential_list = []

        for i, stop in enumerate(self.bus_stops):
            stop_set = {}
            stop_set['stop_id'] = i
            stop_set['stop_name'] = stop
            tempList = []
            for item in self.ik_list:
                if item['from_stop_name'] == stop_set['stop_name'] and item['time_gap'] >= minGap:
                    tempList.append({'ik': str(int(item['block_num']))+'_'+str(item['sequence_id']-1), 'time_gap': item['time_gap'], 'bus_stop_time': item['bus_stop_time'], 'bus_start_time': item['bus_start_time'], 'bus_stop_time_int': item['bus_stop_time'].hour*60+item['bus_stop_time'].minute, 'bus_start_time_int': item['bus_start_time'].hour*60+item['bus_start_time'].minute})
            if len(tempList) > 0:
                tempList = sorted(tempList, key=lambda result: result['bus_stop_time_int'])
                stop_set['ik_time_gap'] = tempList
                potential_list.append(stop_set)
                self.potential_bus_stops.append({'stop_name': stop_set['stop_name'], 'stop_id': stop_set['stop_id']})
                self.potential_bus_sets[stop_set['stop_id']] = stop_set['stop_name']

        print (potential_list)
        return potential_list

    def conflict_bus_at_stop(self, charge_time = TIMEGAP):

        potential_stops = self.generate_potential_station()

        conflict_at_stop_list = []
        for stop in potential_stops:
            tempset = {'stop_id': stop['stop_id']}
            tempList = []
            dup = set()
            for i,item in enumerate(stop['ik_time_gap']):
                start_time = item['bus_stop_time_int']
                end_time = item['bus_start_time_int']

                if i == len(stop['ik_time_gap']) - 1:
                    continue
                bus_i_stop_time_int = item['bus_stop_time_int']
                bus_i_start_time_int = item['bus_start_time_int']
                conflict_with_ik = {'bus_ik': item['ik'], 'bus_ik_stop_time_int': bus_i_stop_time_int, 'bus_ik_start_time_int': bus_i_start_time_int}
                tmp_conflict_list = []
                for j in range(i+1,len(stop['ik_time_gap'])):
                    # check conflict
                    if (stop['ik_time_gap'][j]['bus_stop_time_int'] - bus_i_stop_time_int < 10) and (abs(stop['ik_time_gap'][j]['bus_start_time_int'] - bus_i_start_time_int) < 10) and item['time_gap']< (charge_time*2) and stop['ik_time_gap'][j]['time_gap'] < (charge_time*2) and ((stop['ik_time_gap'][j]['bus_start_time_int'] < bus_i_start_time_int and stop['ik_time_gap'][j]['bus_start_time_int'] - bus_i_stop_time_int < (charge_time * 2) and bus_i_start_time_int - stop['ik_time_gap'][j]['bus_stop_time_int'] < (charge_time * 2)) or (stop['ik_time_gap'][j]['bus_start_time_int'] > bus_i_start_time_int and stop['ik_time_gap'][j]['bus_start_time_int'] - bus_i_stop_time_int < (charge_time * 2))):
                    #and (stop['ik_time_gap'][j]['ik'] not in dup) and (item['ik'] not in dup):

                        dup.add(stop['ik_time_gap'][j]['ik'])
                        tmp_conflict_list.append({'bus_ik': stop['ik_time_gap'][j]['ik'], 'bus_ik_stop_time_int':stop['ik_time_gap'][j]['bus_stop_time_int'], 'bus_ik_start_time_int': stop['ik_time_gap'][j]['bus_start_time_int']})
                        end_time = stop['ik_time_gap'][j]['bus_start_time_int']

                if len(tmp_conflict_list) != 0:
                    conflict_with_ik['conflict_with_ik_list'] = tmp_conflict_list
                    conflict_with_ik['conflict_time_range'] = str(start_time)+'-'+str(end_time)
                    tempList.append(conflict_with_ik)
            if len(tempList) != 0:
                tempset['conflicts'] = tempList
                conflict_at_stop_list.append(tempset)

        return conflict_at_stop_list


    def generate_ik(self):

        resultList = []
        count_sequence = 2
        last_block_num = ""
        for i,item in enumerate(self.xlsx_info):
            if i!= 0 and (item['block_num'] == last_block_num):
                if item['from_stop'] != self.xlsx_info[i-1]['to_stop']:
                    resultList.append({'block_num':item['block_num'], 'sequence_id':count_sequence, 'from_stop_name': item['from_stop'], 'stop_name': item['from_stop'], 'time_gap': -1, 'dis': 0, 'FromTime': item['R_FromTime'], 'ToTime': item['R_ToTime']})

                    # sequence map to time and stop name
                    self.sequenceTimeList['X'+str(int(item['block_num']))+'_'+str(count_sequence)] = {'stop_name': item['from_stop'], 'time': item['R_FromTime']}

                    # stop name map to a list of {'sequence', 'time'}
                    if item['from_stop'] in self.stop_sequnceTimeList.keys():
                        self.stop_sequnceTimeList[item['from_stop']].append({'sequenceId': 'X'+str(int(item['block_num']))+'_'+str(count_sequence), 'time': item['R_FromTime']})
                    else:
                        self.stop_sequnceTimeList[item['from_stop']] = [{'sequenceId': 'X'+str(int(item['block_num']))+'_'+str(count_sequence), 'time': item['R_FromTime']}]

                    count_sequence += 1

                resultList.append({'block_num':item['block_num'], 'sequence_id':count_sequence, 'from_stop_name': item['from_stop'], 'stop_name': item['to_stop'], 'time_gap': round((item["FromTime"] * 24 * 3600 - self.xlsx_info[i-1]["ToTime"]*24*3600)/60), 'bus_stop_time': self.xlsx_info[i-1]['R_ToTime'], 'bus_start_time': item['R_FromTime'], 'dis': item['Length'], 'FromTime': item['R_FromTime'], 'ToTime': item['R_ToTime']})

                self.sequenceTimeList['X'+str(int(item['block_num']))+'_'+str(count_sequence)] = {'stop_name': item['to_stop'], 'time': item['R_ToTime']}

                if item['to_stop'] in self.stop_sequnceTimeList.keys():
                    self.stop_sequnceTimeList[item['to_stop']].append({'sequenceId': 'X'+str(int(item['block_num']))+'_'+str(count_sequence), 'time': item['R_ToTime']})
                else:
                    self.stop_sequnceTimeList[item['to_stop']] = [{'sequenceId': 'X'+str(int(item['block_num']))+'_'+str(count_sequence), 'time': item['R_ToTime']}]

                count_sequence += 1

            else:
                count_sequence = 2
                resultList.append({'block_num':item['block_num'], 'sequence_id':0, 'from_stop_name': item['from_stop'], 'stop_name': item['from_stop'], 'time_gap': -1, 'dis': 0, 'FromTime': item['R_FromTime'], 'ToTime': item['R_ToTime']})

                self.sequenceTimeList['X'+str(int(item['block_num']))+'_'+str(count_sequence)] = {'stop_name': item['from_stop'], 'time': item['R_FromTime']}

                if item['from_stop'] in self.stop_sequnceTimeList.keys():
                    self.stop_sequnceTimeList[item['from_stop']].append({'sequenceId': 'X'+str(int(item['block_num']))+'_0', 'time': item['R_FromTime']})
                else:
                    self.stop_sequnceTimeList[item['from_stop']] = [{'sequenceId': 'X'+str(int(item['block_num']))+'_0', 'time': item['R_FromTime']}]

                resultList.append({'block_num':item['block_num'], 'sequence_id':1, 'from_stop_name': item['to_stop'], 'stop_name': item['to_stop'], 'time_gap': -1, 'dis': item['Length'], 'FromTime': item['R_FromTime'], 'ToTime': item['R_ToTime']})

                self.sequenceTimeList['X'+str(int(item['block_num']))+'_'+str(count_sequence)] = {'stop_name': item['to_stop'], 'time': item['R_ToTime']}

                if item['to_stop'] in self.stop_sequnceTimeList.keys():
                    self.stop_sequnceTimeList[item['to_stop']].append({'sequenceId': 'X'+str(int(item['block_num']))+'_1', 'time': item['R_ToTime']})
                else:
                    self.stop_sequnceTimeList[item['to_stop']] = [{'sequenceId': 'X'+str(int(item['block_num']))+'_1', 'time': item['R_ToTime']}]

            last_block_num = item['block_num']

        self.ik_list = resultList

    def create_stop_set(self):

        resultList = self.ik_list
        #self.write_xls(resultList, ['block_num', 'sequence_id', 'stop_name'], '../output/UTA_Runcut_stop_set', sheetName = 'Aug2016')
        stop_set_list = []
        for i, stop in enumerate(self.potential_bus_stops):
            stop_set = {}
            stop_set['stop_id'] = stop['stop_id']
            stop_set['stop_name'] = stop['stop_name']
            tempList = []
            for item in resultList:
                if item['stop_name'] == stop_set['stop_name']:
                    tempList.append(item)

            stop_set['omega'] = tempList
            stop_set_list.append(stop_set)


        # print stop_set_list

        return stop_set_list


    def generate_accumulate_dis(self):

        ik_list = self.ik_list
        accu_list = []

        cur_block_num = 0
        cur_dis = 0.0
        tmp_dict = dict()
        tmp_dict['accu_dis_list'] = []

        for ik_item in ik_list:
            if ik_item['block_num'] != cur_block_num:
                cur_block_num = ik_item['block_num']
                accu_list.append(tmp_dict)
                tmp_dict = dict()
                cur_dis = 0.0
                tmp_dict['block_num'] = ik_item['block_num']
                tmp_dict['accu_dis_list'] = []

            cur_dis += ik_item['dis']
            tmp_dict['accu_dis_list'].append({'seq_id': str(int(ik_item['block_num']))+'_'+str(ik_item['sequence_id']), 'accu_dis': cur_dis})

        accu_list.append(tmp_dict)
        #print (accu_list)
        return accu_list


    '''
    Write file functions
    '''
    def write_conflict_bus(self):

        conflict_list = self.conflict_bus_at_stop()
        with open("conflict_output_new.txt", "w") as text_file:
            text_file.write('stop_id time_range conflict_ids\n\n')
            for item in conflict_list:
                stop_id = item['stop_id']
                for iks in item['conflicts']:
                    time_range = iks['conflict_time_range']
                    conflict_ik_str = iks['bus_ik']
                    for ciks in iks['conflict_with_ik_list']:
                        conflict_ik_str += (',' + ciks['bus_ik'])

                    text_file.write(str(stop_id) + ' ' + time_range + ' ' + conflict_ik_str+'\n')

    def write_stop_set(self):
        stop_set_list = self.create_stop_set()
        with open("ik_j_set_new.txt", "w") as text_file:
            text_file.write('stop_id iks\n\n')
            for item in stop_set_list:
                stop_id = item['stop_id']
                stop_name = item['stop_name']
                iks_str = ''
                for iks in item['omega']:
                    iks_str += str(int(iks['block_num']))+'_'+str(iks['sequence_id']) + ','

                text_file.write(str(stop_id) + '  '+ iks_str[:-1] +'\n\n')

    def write_potential_stop(self):
        self.write_xls(self.potential_bus_stops, ['stop_id', 'stop_name'], './output/UTA_Runcut_Potential_Stop')


    '''
        write gurobi lp file.
    '''

    def write_gurobi_lp(self, output_dir, max_bus=1, max_length=62, time_type='WEEKDAY'):

        # All strings.
        # Initiate
        lp_file_str = ''

        outputStr = 'Maximize\n'
        lp_file_str += outputStr
        # write object.

        self.cal_distance_for_bus(run_time_type=time_type)
        self.write_potential_stop()
        busList = self.filter_by_single_route_length() + self.bus_not_need_charged
        # busList consists of buses that satisfy the mileage constraint (distance between two on-route charging stations are below 62, the  maximum range we assume)
        # If you trace back the function above, please ignore the value 251. It does not play any role here.

        # have to do generate ik list first.
        self.generate_ik()
        self.generate_potential_station()

        # This gives out the potential stop where buses dwell more than 10 minutes, which is the charging time we assume.
        self.write_potential_stop()
        # print len(busList)

        Z_str = ''
         Y_str = ''
        stopsStr = ''
        df = pd.read_csv("Ei_for_blocks.csv") # the weighted population we calculated

        # 1 is the price of one on-route charging station
        # 0.749 is the price of purchasing a BEB  #BIAO 0.79 was used in the paper
        # 0.35 is the price of building one in-depot charging station,
        # the number of buses replaced determines the number of in-depot charging stations entirely
        # We only need a variable that shows the number of in-depot charging stations.
        for stop_item in self.potential_bus_stops:
            stopsStr += '1 ' + 'Y' + str(stop_item['stop_id']) + ' + '
            Y_str += 'Y' + str(stop_item['stop_id']) + ' '
        print(stopsStr)
        busStr = ''
        ei_str = ''
        budget = ''
        for bus_item in busList:
            Z_str += 'Z' + str(int(bus_item['block_num'])) + ' '
            busStr += '0.749 Z' + str(int(bus_item['block_num'])) + ' + '
            ei_str += str(df.loc[df["block_num"] == int(bus_item['block_num'])].iloc[0, 1]) + ' ' + 'Z' + str(int(bus_item['block_num'])) + ' + ' #BIAO objective (1)
        # print ('stop_count:', len(self.potential_bus_stops))

        lp_file_str += ei_str[:-3]
        # I is the number of in-depot charging stations

        budget = stopsStr + busStr[:-3] + ' + 0.35 I'         #BIAO objective (2)
        # print (stopsStr)
        # print (busStr[:-3])

        # print (self.ik_list)

        subject_to = '\nSubject To\n'
        lp_file_str += subject_to
        # write subject.

        total_len = self.sum_timeAndLength()
        # print (total_len)
        accu_dis_list = self.generate_accumulate_dis()

        str1 = ''
        str2 = ''
        str3 = ''
        str4 = ''
        # new added
        str5 = ''
        # new added  xik <= Zi constraint.
        xzconstraint = ''

        str_lastStop = ''

        for sum_item in total_len:
            Mi = round(sum_item['total_length'], 2) + 1
            Zi = 'Z' + str(int(sum_item['block_num']))
            str2 += 'm' + str(int(sum_item['block_num'])) + '_' + '0 = 0\n' #Biao (4)
            for i, item in enumerate(accu_dis_list):
                if i == 0:
                    continue
                if item['block_num'] == sum_item['block_num']:

                    str_lastStop += 'X' + item['accu_dis_list'][len(item['accu_dis_list']) - 1]['seq_id'] + ' = 0\n'
                    for j, accu_item in enumerate(item['accu_dis_list']):
                        mik = 'm' + accu_item['seq_id']
                        xik = 'X' + accu_item['seq_id']
                        # str1 = mik + ' + ' + Zi + ' <= ' + str(Mi+max_length) + '\n'
                        str5 += mik + ' + ' + str(Mi) + ' ' + xik + ' <= ' + str(Mi) + '\n'
                        xzconstraint += xik + ' - ' + Zi + ' <= 0\n'   #Biao (9)

                        if j != 0:
                            dis = round(accu_item['accu_dis'] - item['accu_dis_list'][j - 1]['accu_dis'], 2)
                            mik_last = 'm' + item['accu_dis_list'][j - 1]['seq_id']
                            str1 += mik_last + ' + ' + str(Mi) + ' ' + Zi + ' <= ' + str(Mi + max_length - dis) + '\n'  #Biao (7)
                            str3 += mik + ' - ' + mik_last + ' <= ' + str(dis) + '\n'   #Biao (5)
                            str4 += mik + ' - ' + mik_last + ' + ' + str(Mi) + ' ' + xik + ' >= ' + str(dis) + '\n' #Biao (6)


        lp_file_str += str1 + str2 + str3 + str4 + str5 + str_lastStop + xzconstraint

        # create stop set (5)
        stop_set_list = self.create_stop_set()
        stop_set_str = ''

        for item in stop_set_list:
            stop_id = item['stop_id']
            stop_name = item['stop_name']
            iks_str = ''
            xzconstraint += 'Y' + str(stop_id)
            for iks in item['omega']:
                stop_set_str += 'X' + str(int(iks['block_num'])) + '_' + str(iks['sequence_id']) + ' - ' + 'Y' + str(
                    stop_id) + ' <= 0\n'
                xzconstraint += ' - ' + 'Z' + str(int(iks['block_num']))
            xzconstraint += ' <= 0\n'


        lp_file_str += stop_set_str

        # conflict time (6)
        conflict_list = self.conflict_bus_at_stop()
        conflict_str = ''
        for item in conflict_list:
            stop_id = item['stop_id']
            for iks in item['conflicts']:
                tmp_str = ''
                time_range = iks['conflict_time_range']
                for ciks in iks['conflict_with_ik_list']:
                    tmp_str += 'X' + ciks['bus_ik'] + ' + '

                conflict_str += tmp_str[:-3] + ' - ' + 'Y' + str(stop_id) + ' <= 0\n'   #Biao (8)
                # need to modify here, in our model, on-route charging stations can only charge one BEB simultaneously.


        lp_file_str += conflict_str

        # constraint for in-depot charging stations.
        # we assume that one in-depot charging stations can serve 3 BEB
        indepot_str = ''
        for bus_item in busList:
            indepot_str += 'Z' + str(int(bus_item['block_num'])) + ' + '

        indepot_str = indepot_str[:-3] + ' - 3 I <= 0' + '\n'
        lp_file_str += indepot_str

        # (8)
        # max_bus here is the original p in the previous paper. It's actually the budget here.
        budget_str = budget + ' <= ' + str(max_bus) + '\n'
        lp_file_str += budget_str

        # (9)

        str9 = ''
        for ik_item in self.ik_list:
            flag = True
            xik = 'X' + str(int(ik_item['block_num'])) + '_' + str(ik_item['sequence_id'])
            Xik_str += xik + ' '
            for stop_item in self.potential_bus_stops:
                if ik_item['stop_name'] == stop_item['stop_name']:
                    flag = False
            if flag:
                str9 += xik + ' = 0\n'

        lp_file_str += str9

        # (10) filter unfeasible block_num by time gap.

        str10 = ''
        unfeasible_buses = self.filter_bus_by_time()

        for bus in unfeasible_buses:
            str10 += 'Z' + bus + ' = 0\n'
        lp_file_str += str10

        # (11)

        str11 = ''
        for item in self.ik_list:

            block_num = str(int(item['block_num']))
            if item['time_gap'] != -1 and item['time_gap'] < TIMEGAP:
                str11 += 'X' + block_num + '_' + str(item['sequence_id'] - 1) + ' = 0\n'

        lp_file_str += str11

        lp_file_str += '\nGenerals\n'

        lp_file_str += Y_str[:-1] + ' I'

        str_binary = '\nBinary\n'

        lp_file_str += str_binary

        # print (Xik_str)

        lp_file_str += Z_str + Xik_str + '\nEnd\n'

        with open(output_dir + "/ele_bus_v61.lp", "w") as text_file:
            text_file.write(lp_file_str)
        
def output_bus_type(output_dir, bus_stops, bus_routes, xlsx_file):


    if(platform.system() == sys_windows):
        output_dir = output_dir.replace("/", "\\")
    total_list = []

    sheetNames = ['applicable','one_route', 'less_than_62', 'less_than_251', 'larger_than_251']

    total_sheetNames = []
    for time_type in BUS_RUNINING_TIME_TYPE:
        eb = EleBus(bus_stops, bus_routes, xlsx_file)

        eb.cal_distance_for_bus(run_time_type = time_type)
        for sheet in sheetNames:
            total_sheetNames.append(sheet + '_' + time_type)
        busList = eb.filter_by_single_route_length()

        #print ('app: ', len(busList))
        #print ('single: ', len(eb.bus_single_route_filtered))
        #print ('<62: ', len(eb.bus_not_need_charged))
        #print ('<251: ', len(eb.less_than_251))
        #print ('>251: ', len(eb.cant_charged))

        total_list.append(busList)
        total_list.append(eb.bus_single_route_filtered)
        total_list.append(eb.bus_not_need_charged)
        total_list.append(eb.less_than_251)
        total_list.append(eb.cant_charged)

    #print (busList)

    #print (total_sheetNames)
    eb.write_xls_multi_sheets(total_list, sheetNames = total_sheetNames, fileName = output_dir + '/UTA_Runcut_bus_type_all_new')

    print ("success!")
    return
#    print (eb.bus_not_need_charged)
    #print (eb.bus_single_route_filtered)

def output_result_all(glpk_file, bus_stops, bus_routes, xlsx_file, output_dir, bus_num_dict = {'SUNDAY': 0, 'SATURDAY': 0, 'WEEKDAY':0}):

    if(platform.system() == sys_windows):
        output_dir = output_dir.replace("/", "\\")

    resultLists = []


    fgx = '\n--------------------------------------------\n\n'

    '''

    SUNDAY: 52(48)
    SATURDAY: 148(120)
    WEEKDAY: 305(221)

    '''

    type_times_dict = {'SUNDAY':49, 'SATURDAY':121, 'WEEKDAY': 222}

    for run_time_type in BUS_RUNINING_TIME_TYPE:

        output_str = ''
        num = bus_num_dict[run_time_type]
        if num == 0:
            continue
        for i in range(num,num+1):#type_times_dict[run_time_type]):
            block_nums_set = set()
            stop_set = set()
            stop_id_name_list = []
            sequence_id_set = set()

            resultDict = dict()
            #print (i)
            eb = EleBus(bus_stops, bus_routes, xlsx_file)

            eb.write_gurobi_lp(output_dir, max_bus=i, time_type = run_time_type)
            obj_val, bus_resultList, stop_resultList, sequence_list = op.optimize(glpk_file, output_dir + '/ele_bus_v61.lp' , output_dir + '/ele_bus_result_all_v61.txt')

            for item in sequence_list:
                sequence_id_set.add(item)

            output_str += 'Number of buses: ' + str(i) + '\n'
            resultDict['num_of_line'] = i
            output_str += 'Object value: ' + str(obj_val) + '\n'
            resultDict['val'] = obj_val
            tmp_bus_str = ''

            for bus in bus_resultList:
                block_nums_set.add(bus)
                tmp_bus_str += str(bus) + ' ,'
            output_str += 'Block_nums: ' + tmp_bus_str[:-2] + '\n'
            resultDict['block_nums'] = bus_resultList

            tmp_stop_str = ''
            for stop in stop_resultList:
                if eb.potential_bus_sets[stop] not in stop_set:
                    stop_set.add(eb.potential_bus_sets[stop])
                    stop_id_name_list.append((stop, eb.potential_bus_sets[stop]))
                tmp_stop_str += '[ id: ' + str(stop) + ' ' + 'name: ' + str(eb.potential_bus_sets[stop]) + ' ]' + ' ,'

            #print (tmp_stop_str[:-2])
            output_str += 'Stops: ' + tmp_stop_str[:-2] + '\n'
            resultDict['stops'] = stop_resultList
            resultDict['stops_names'] = [eb.potential_bus_sets[i] for i in stop_resultList]

            output_str += fgx

            eb.matchStops()
            eb.write_bus_line_shp(block_nums_set, output_dir + '/shpfile_new/'+run_time_type+'/'+str(i)+'/UTA_Runcut_bus_'+str(i))
            eb.write_result_shp(sequence_id_set, output_dir + '/shpfile_new/'+run_time_type+'/'+str(i)+'/UTA_Runcut_stop_'+str(i))
            eb.write_bus_line_adj_shp(block_nums_set,  output_dir + '/shpfile_new/'+run_time_type+'/'+str(i)+'/UTA_Runcut_bus_adj'+str(i), field = ['ID'])

        # with open("ele_bus_gurobi_results_"+ run_time_type +".txt", "w") as text_file:
        #     text_file.write(output_str)

    return stop_id_name_list, block_nums_set, sequence_id_set


def generate_result_routes():

    bustype = ['SATURDAY', 'SUNDAY', 'WEEKDAY']

    bustype_list = {'SATURDAY': [], 'SUNDAY': [], 'WEEKDAY': []}

    #eleBus= EleBus()

    for t in bustype:

        line_dict_list = []
        file = open("../output/Ele_Gurobi_shpfile/ele_bus_gurobi_results_" + t + ".txt", "r")
        lines = file.readlines()
        line_num = 0
        while line_num < len(lines):
            line_dict = dict()
            line_dict['Number of buses'] = int(lines[line_num].split(":")[1].strip(" ").strip("\n"))
            block_num_raw_list = lines[line_num+2].split(":")[1].split(",")
            block_num_list = [int(l.strip(" ").strip("\n")) for l in block_num_raw_list]
            line_dict['Block_nums'] = block_num_list
            stop_list = lines[line_num+3].split(",")
            stop_int_list = []
            for stop in stop_list:
                stop_id = stop[stop.find("id")+4 : stop.find("id")+6]
                stop_int_list.append(int(stop_id))

            line_dict['Stops_list'] = stop_int_list
            line_dict['Stops_num'] = lines[line_num+3].count("id")
            line_dict_list.append(line_dict)
            line_num += 7

        station_results_dict = dict()
        for line in line_dict_list:
            if line['Stops_num'] not in station_results_dict.keys():
                station_results_dict[line['Stops_num']] = []
            station_results_dict[line['Stops_num']].append(line)

        for k,v in station_results_dict.items():
            station_results_dict[k] = v[-1]

        # get xlsx infomation to match block_num to routes.
        eb = EleBus()
        xlsx_list = eb.read_Runcut_xlsx(t)

        for k,v in station_results_dict.items():
            route_abbr_set = set()
            for v_item in v['Block_nums']:
                for xlsx_item in xlsx_list:
                    if v_item == int(xlsx_item['block_num']):
                        route_abbr_set.add(xlsx_item['LineAbbr'])
            v['route_set'] = route_abbr_set
            v['routes_num'] = len(route_abbr_set)
            station_results_dict[k] = v

        routes_info = eb.read_routes()
        reader = shapefile.Reader('../resources/BusRoutes_UTA_Jan_2017/BusRoutes_UTA.shp')
        routes_record = reader.shapes()

        abbr_info_dict = dict()
        for i,value in enumerate(routes_info):
            raw_points = routes_record[i].points
            # print (routes_record[i].shape.points)
            # filter_points = []
            # for i,points in enumerate(raw_points):
            #     if i%2 == 0:
            #         filter_points.append(points)
            # filter_points.append(raw_points[0])
            value['shape_points'] = raw_points
            abbr_info_dict[value['LineAbbr']] = value

        for k,v in station_results_dict.items():
            bustype_list[t].append({'Number of charging stations': k, 'Number of electric buses': v['Number of buses'], 'Number of routes': v['routes_num']})
            # if k!=1:
            #     continue

            output_str = ''
            stop_str = ''
            for stop in v['Stops_list']:
                stop_str += str(stop) + ' '

            with open("../output/stations/"+ t +"/"+ str(k)+"station_"+ t + ".txt", "w") as text_file:
                text_file.write(stop_str)

            for route in v['route_set']:
                output_str += route + ' '
            with open("../output/routes/"+ t +"/"+ str(k)+"station_routes_"+ t + ".txt", "w") as text_file:
                text_file.write(output_str)
            # print (k)
            # print (v)

            # write_routes_shp(abbr_info_dict, '../output/Ele_Gurobi_threshold_shp/'+ t +'/charging_station_'+ str(k) + '/Ele_Gurobi_routes_shp_' + str(k), v['route_set'])
        #print (saturday_list)

    #eleBus.write_xls_multi_sheets([bustype_list['SATURDAY'], bustype_list['SUNDAY'], bustype_list['WEEKDAY']], fieldnames = ['Number of charging stations', 'Number of electric buses', 'Number of routes'], sheetNames = bustype, fileName = '../output/UTA_Runcut_bus_threshold')



'''
write shp files.

'''
def write_routes_shp(abbr_info_dict, fileName, resultSets, field = ['LineAbbr', 'Shape_Lneg', 'LineName', 'Frequency', 'Service']):

        shp_writer = shapefile.Writer(shapefile.POLYLINE)
        shp_writer.autoBalance = 1
        for f in field:
            shp_writer.field(f, 'C', '60')

        for result in resultSets:
            v = abbr_info_dict[result]
            #print (v['shape_points'])
            shp_writer.poly(parts=[v['shape_points']])
            shp_writer.record(v['LineAbbr'], v['Shape_Leng'], v['LineName'], v['Frequency'], v['Service'])
        shp_writer.save(fileName)
        print ('write succeed!')

#generate_result_routes()

#edit_routes_shp()

#eb = EleBus()

#stop_set, block_num_set, sequence_set  = output_result_all()



# eb.cal_distance_for_bus('WEEKDAY')
# eb.filter_by_single_route_length()
# # # # have to do generate ik list first.
# eb.generate_ik()
# eb.generate_potential_station()

# # #eb.filter_bus_by_time()
# # # # eb.create_stop_set()
# # # # eb.write_stop_set()
# # # eb.write_conflict_bus()
# # # t = time(5, 10)
# # # print (t.minute)
# # #eb.filter_by_length()
# # #eb.sum_timeAndLength()
# # eb.filter_by_single_route_length()
# eb.matchStops()
# #eb.write_station_2D_shp([], '../output/bus_station_2D/bus_station_2D_WEEKDAY')
# #eb.write_result_shp(sequence_set)


# test reader.

# testReader = shapefile.Reader('../output/UTA_Runcut_Guroby_stop.shp')

# print (testReader.shapes()[0].z)
