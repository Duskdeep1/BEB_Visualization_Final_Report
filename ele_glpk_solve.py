import os, platform

sys_windows = "Windows"

#glpk_path = '/usr/local/bin/glpsol --lp '

def optimize(glpk_path, lp_file, result_file):

    if(platform.system() == sys_windows):
        lp_file = lp_file.replace("/", "\\")
        result_file = result_file.replace("/", "\\")

    glpk_path += " --lp "

    os.system(glpk_path + lp_file + ' -o ' + result_file)

    obj_val = 0.0
    xSol = []
    ySol = []
    zSol = []

    with open(result_file) as d:
        flag = 0
        for line in d:
            if line.startswith('Objective'):
                obj_val = line.strip("\n\t").split(' ')[4]
            if "Column name" in line:
                flag = 1
                continue

            if "Integer feasibility" in line:
                flag = 0

            data = line.strip("\n\t").split(' ')
            real_data = []
            for word in data:
                if word!='' and word!= '*':
                    real_data.append(word)

            print (real_data)
            if real_data!=[] and ('-' not in real_data[0]) and flag == 1 and float(real_data[2]) > 0.9:
                if real_data[1].startswith("X"):
                    xSol.append(real_data[1])
                if real_data[1].startswith("Y"):
                    ySol.append(int(real_data[1].split("Y")[1]))
                if real_data[1].startswith("Z"):
                    zSol.append(int(real_data[1].split("Z")[1]))


    return (obj_val, zSol, ySol, xSol)
