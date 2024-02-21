import plistlib
import pandas as pd
import os
import sys
import sqlite3
from sqlite3 import Error
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFileDialog, QPushButton, QCheckBox, QComboBox, QLabel

class mainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.project_choose_layout = QHBoxLayout()
        self.silverstack_layout = QVBoxLayout()
        self.label_silverstack_session = QLabel("Choose a Silverstack Project")
        self.base_silverstack_path = "~/Library/Application Support/Pomfort/Silverstack8/Project-"
        self.silverstack_project_list = get_silverstack_project_list()
        self.combo_silverstack_session = QComboBox()
        for project in self.silverstack_project_list:
            self.combo_silverstack_session.addItem(project['name'], project['id'])
        self.combo_silverstack_session.activated.connect(self.debug_combo)
        self.combo_silverstack_session.activated.connect(self.choose_silverstack_project)
        self.silverstack_layout.addWidget(self.label_silverstack_session)
        self.silverstack_layout.addWidget(self.combo_silverstack_session)
        self.project_choose_layout.addLayout(self.silverstack_layout)

        self.browse_day_of_shooting_button = QPushButton("Browse ZoeLog CSV")
        self.browse_day_of_shooting_button.clicked.connect(self.browse_day_of_shooting_folder)
        self.project_choose_layout.addWidget(self.browse_day_of_shooting_button)

        self.check_box_layout = QVBoxLayout()
        self.label_check_box = QLabel("Choose the meta to import from zoelog")
        self.check_box_layout.addWidget(self.label_check_box)

        self.launch_button_layout = QHBoxLayout()
        self.launch_button_edit_silverstack = QPushButton("Launch Silverstack Edit")
        self.launch_button_edit_silverstack.clicked.connect(self.launch_silverstack_edit)
        self.launch_button_layout.addWidget(self.launch_button_edit_silverstack)
        self.erase_check_box = QCheckBox("Erase when editing metadata")
        self.erase_check_box.setChecked(True)
        self.launch_button_layout.addWidget(self.erase_check_box)

        self.main_layout.addLayout(self.project_choose_layout)
        self.main_layout.addLayout(self.check_box_layout)
        self.main_layout.addLayout(self.launch_button_layout)

    def debug_check_box(self):
        for check_box in self.check_box_list:
            print(check_box.text(), check_box.isChecked())

    def debug_combo(self):
        print(type(self.combo_silverstack_session.currentData()))
        print(self.combo_silverstack_session.currentData())

    def browse_day_of_shooting_folder(self):
        self.day_folder_path = QFileDialog().getExistingDirectory(self, "Browse Day of Shooting Folder", "/Volumes")
        list_columns_zoelog = ['Roll', "Clip", "Scene", "Take", "Lens", "Lens Type", "Filters", "Description", "Notes"]
        if self.day_folder_path != "":
            for root, dirs, files in os.walk(self.day_folder_path):
                for file in files:
                    if file.endswith(".csv"):
                        print(os.path.join(root, file))
                        df = pd.read_csv(os.path.join(root, file), error_bad_lines=False)
                        # csv_file = csv.reader(os.path.join(root, file))
                        # csv_headers = next(csv_file)
                        if all([i in df.columns for i in list_columns_zoelog]):
                            self.zoelog_path = os.path.join(root, file)
                            break
            self.zoe_meta_dict, list_meta = create_dict_from_zoelog_csv(self.zoelog_path)
            # self.zoelog_df = pd.DataFrame.from_dict(self.zoe_meta_dict, orient='index') ????
            self.check_box_list = []
            for meta in list_meta:
                meta_box = QCheckBox(meta)
                meta_box.setChecked(True)
                meta_box.clicked.connect(self.debug_check_box)
                self.check_box_layout.addWidget(meta_box)
                self.check_box_list.append(meta_box)
            self.main_layout.addLayout(self.check_box_layout)

    def choose_silverstack_project(self):
        self.current_silverstack_project_name = self.combo_silverstack_session.currentData()
        self.current_silverstack_project_path_db = os.path.expanduser(
            f"{self.base_silverstack_path}{self.current_silverstack_project_name}/Silverstack.psdb")

    def launch_silverstack_edit(self):
        # database = "material/Project-278CF5FB1D6B/Silverstack.psdb"
        # create a database connection
        # database = "/Users/bryanrandell/Library/Application Support/Pomfort/Silverstack8/Project-89C21C3CB548/Silverstack.psdb"
        # zoe_log_csv = "/Users/bryanrandell/PycharmProjects/tnl_check_data/material/TheNewLook-2022-11-02.csv"
        if self.day_folder_path != "":
            conn = create_connection(self.current_silverstack_project_path_db)
            with conn:
                edit_silverstackdb(conn, self.zoe_meta_dict, erase_data=self.erase_check_box.isChecked())
        else:
            print("Please choose a zoelog csv file")


def findSilverstackInstances():
    if sys.platform != "darwin":
        return "Error: You are not working on an compatible OS. Only MacOS 10.15.7 or higher is supported"
    else:
        pomfortFolder = os.path.expanduser('~/Library/Application Support/Pomfort/')
        try:
            subFolders = os.listdir(pomfortFolder)
        except FileNotFoundError:
            return "Error: Silverstack doesn't appear to be installed on your system"
        instances = []
        for Folder in subFolders:
            if Folder.startswith('Silverstack8'):
                instances.append(Folder)
        if len(instances) == 0:
            return "Error: No compatible Silverstack Instance has been found installed on your System"
        else:
            return instances


def get_silverstack_project_list():
    instance = findSilverstackInstances()[0]
    pathToInstance = os.path.expanduser('~/Library/Application Support/Pomfort/' + instance + '/')
    projectFolders = os.listdir(pathToInstance)
    project_list = []
    for project in projectFolders:
        if project.startswith('Project-'):
            path = pathToInstance + project
            file = open(path + '/Project.plist', 'rb')
            plist = plistlib.load(file)
            file.close()
            project_list.append({
                'id': project.rsplit('-')[1],
                'name': plist['name'],
                'instance': instance,
                'creationDate': plist['creationDate']
            })
    return project_list


def create_dict_from_zoelog_csv(zoe_log_csv_path: str) -> dict:
    """
    Create a dict with scene as key and take as value
    :param zoe_log_csv_path: csv generated by zoelog
    :return: a dict with clip as key and list of data as values
    list indexes are : 0: roll, 1: clip, 2: scene, 3: take, 4: lens, 5: lens type, 6: filter, 7: Desc, 8: Notes
    """
    df = pd.read_csv(zoe_log_csv_path)
    list_columns_zoelog = ['Roll', "Clip", "Scene", "Take", "Lens", "Lens Type", "Filters", "Description", "Notes"]
    if all([i in df.columns for i in list_columns_zoelog]):
        sample = df[['Roll', "Clip", "Scene", "Take", "Lens", "Lens Type", "Filters", "Description", "Notes"]]
        unsorted_dict = {}
        for data in sample.values:
            cam_clip = f"{data[0]}C{data[1]:03d}"
            unsorted_dict[cam_clip] = [i for i in data]
        return dict(sorted(unsorted_dict.items())), list_columns_zoelog
    else:
        return {"Error": "The zoelog csv is not compatible with this script"}


def get_zpk_from_silverstack_database(conn, zname, camera_type="SONY"):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute(f"SELECT Z_PK FROM ZRESOURCEOWNER WHERE ZNAME LIKE '{zname}%' AND ZCODEC LIKE '{camera_type}%';")
    rows = cur.fetchall()
    return rows[0][0]


def edit_silverstackdb(conn, zoelog_dict: dict, camera_type: str="Sony", erase_data:bool=True) -> bool:
    """
    already exist in silverstack but not very reliable, doesn't seems to match very well
    modify silverstack database with zoelog dictionnary
    list indexes from zoelog : 0: roll, 1: clip, 2: scene, 3: take, 4: lens, 5: lens type, 6: filter, 7: Desc, 8: Notes
    :return: True if not fail

    Z_PK from ressource owner to retrieve the file entry in ZUSERINFO in the ZRESSOURCEOWNER column
    todo : not erasing the existing data in the database and don't add nan values
    todo : make another loop where every entry is checked and if it's not in the database it's added one at a time
    """
    erase_zressource = ";"
    dont_erase_zressource = """AND ZSCENE IS NULL
                    AND ZTAKE IS NULL
                    AND ZLENS IS NULL
                    AND ZFILTER IS NULL;
                    """
    erase_userinfo = ";"
    dont_erase_userinfo = """AND ZSCENE IS NULL;"""
    for clip in zoelog_dict:
        roll, clip_2, scene, take, lens, lens_type, filter, desc, notes = zoelog_dict[clip]
        sql = f"""
        UPDATE ZRESOURCEOWNER
        SET ZSCENE = '{scene if scene != 'nan' else ''}', 
        ZTAKE = '{take if take != 'nan' else ''}', 
        ZLENS = '{lens if lens != 'nan' else ''} {lens_type if lens_type != 'nan' else ''}', 
        ZFILTER = '{filter if filter != 'nan' else ''}'
        WHERE ZNAME LIKE '{clip}%' 
        AND ZCODEC LIKE '{camera_type}%'
        {erase_zressource if erase_data else dont_erase_zressource}"""
        # print(sql)
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print(f"update {clip} done")
        z_pk = get_zpk_from_silverstack_database(conn, clip)
        print(f"Z_PK = {z_pk}")

        sql_2 = f"""
        UPDATE ZUSERINFO
        SET ZCOMMENT = '{f"{desc if desc != 'nan' else ''} {notes if notes!= 'nan' else ''}"}'
        WHERE ZRESOURCEOWNER = {z_pk}
        {erase_userinfo if erase_data else dont_erase_userinfo}"""
        cur.execute(sql_2)
        conn.commit()
        print(f"update {clip} done")
    return True


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
    return conn


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = mainWindow()
    window.show()
    sys.exit(app.exec_())
