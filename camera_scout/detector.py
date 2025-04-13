import subprocess
import json
import re
from typing import List, Dict, Optional, TypedDict
from pathlib import Path


class CameraResearcher:
    def __init__(
        self,
        config_path: str = "/reference/base_cam_in_company.json",
        visualize: bool = True,
    ):
        """
        Initialize camera researcher with configuration
        :param config_path: Path to JSON file with camera type definitions
        """

        self.__NO_CAM_FOUND: bool = False
        self.__config = self._load_config(config_path)
        self.__codec_preferences = {"cam": "MJPG", "termal": "YUYV"}
        self._detailed_info: Optional[List]
        self._camera_stacks_by_group: Optional[List]

        self._discover_cameras()
        if visualize and not self.__NO_CAM_FOUND:
            self._draw_detailed_info()

    def _load_config(self, path_json: str) -> Dict:
        """Load camera type configuration from JSON file"""
        try:

            search_paths = [
                Path(path_json),
                Path(f"camera_scout/{path_json}"),
                Path(__file__).parent / path_json,
                Path(__file__).parent / "camera_scout/" / path_json,
                Path.cwd() / path_json,
            ]

            for path in search_paths:
                if path.exists():
                    global_path = path
                    break

            with open(global_path, "r") as f:
                return json.load(f)

        except (FileNotFoundError, json.JSONDecodeError, UnboundLocalError) as e:
            raise RuntimeError(
                f"Failed to load camera config: check path to {path_json})"
            )

    def _discover_cameras(self) -> None:
        """Discover all available cameras and analyze their capabilities"""
        self._detailed_info = self._get_detailed_info()
        if not self._detailed_info:
            self.__NO_CAM_FOUND = True
            print("No cameras detected\n")
            return

        self._get_cam_type()
        self._get_best_cam_param()
        self._camera_stacks_by_group = self._group_cameras_by_type()

    def _get_detailed_info(self) -> Optional[List]:
        """Получение и парсинг информации о камерах"""
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                text=True,
            )
            return self._parse_detailed_info(result.stdout)

        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Get error input from v4l2-ctl")
            return None

    def _parse_detailed_info(self, output: str) -> Optional[List]:
        """Парсинг вывода v4l2-ctl в структурированный формат"""

        devices = []
        current_device = {}

        for line in output.splitlines():
            line = line.rstrip()
            if not line:
                continue

            # search cam name
            if not line.startswith((" ", "\t")) and ":/dev/" not in line:
                if current_device:
                    devices.append(current_device)
                current_device = {
                    "name": line.replace(":", "").strip(),
                    "type": "",
                    "paths": [],
                    "_id": [],
                    "cam_param": {},
                }
            # serach id name
            elif line.strip().startswith("/dev/video"):
                current_device["paths"].append(line.strip())

        if current_device:
            devices.append(current_device)
        return devices

    def _get_cam_type(self):
        """Find cam type from json"""
        for device in self._detailed_info:
            device["type"] = self._find_type(device["name"], self.__config)

    def _find_type(self, cam_name: str, fcc_data: json) -> str:
        """Search simulars betwen json and cam name"""
        for cam_type, names in fcc_data.items():
            for name in names:
                if name.lower() in cam_name.lower():
                    return cam_type
        assert "Not find cam type, check .json"

    def _get_best_cam_param(self):
        """find best paramerts for all find cam"""
        for device in self._detailed_info:
            if device["type"] == "realsense" or device["type"] == "":
                continue

            cam_codec = self.__codec_preferences[device["type"]]
            main_path = device["paths"][0]
            cam_id = int(main_path[-1])

            all_specs = self._get_camera_specs(main_path, cam_codec)
            best_specs = all_specs[0]

            device["_id"] = cam_id
            device["cam_param"] = best_specs

    def _get_camera_specs(self, device_path, cam_codec) -> Optional[List]:
        """Получить характеристики камеры для форматов MJPG и YUYV"""
        try:
            result = subprocess.run(
                ["v4l2-ctl", "-d", device_path, "--list-formats-ext"],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout

            specs = []
            current_format = None
            current_res = None

            for line in output.splitlines():
                # Определяем текущий формат
                fmt_match = re.match(r"\s*\[\d+\]:\s+\'(\w+)\'.*", line)
                if fmt_match:
                    current_format = fmt_match.group(1)
                    current_res = None
                    continue

                # Фильтруем только нужные
                if current_format not in {cam_codec}:
                    continue

                # Определяем разрешение
                size_match = re.match(r"\s*Size:\s+Discrete\s+(\d+)x(\d+)", line)
                if size_match:
                    current_res = (int(size_match.group(1)), int(size_match.group(2)))
                    continue

                # Парсим FPS для текущего формата и разрешения
                if current_res:
                    fps_match = re.search(r"\((\d+\.\d+)\s+fps\)", line)
                    if fps_match:
                        fps = float(fps_match.group(1))
                        specs.append(
                            {
                                "format": current_format,
                                "width": current_res[0],
                                "height": current_res[1],
                                "fps": fps,
                            }
                        )
            return specs

        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return []

    def _draw_detailed_info(self) -> None:
        """Draw all usb cameras specifics"""
        print("Cam info:")
        if self._detailed_info:
            for device in self._detailed_info:
                print(f"• {device['name']}")
                print(f"• Cam type: {device['type']}")
                for path in device["paths"]:
                    print(f"  └ {path}")
                print(f"• Cam id: {device['_id']}")

                if len(device["cam_param"]) != 0:
                    cam_param = device["cam_param"]
                    print(f"• Codec fomat: {cam_param['format']}")
                    print(
                        f"• Pixels size: {cam_param['width']}x{cam_param['height']} by {cam_param['fps']} FPS"
                    )
                print()
        else:
            print("Not see cam devices")

    def _group_cameras_by_type(self) -> List:
        """Группирует камеры по типам в стекоподобную структуру"""
        stacks = {"termal": [], "cam": [], "realsense": []}

        for camera in self._detailed_info:
            camera_type = camera["type"]
            stacks[camera_type].append(camera)

        print("All find:")
        for cam_name in stacks:
            print(f"{len(stacks[cam_name])} {cam_name} obj")
        print("")
        return stacks

    def get_camera(self, cam_type):
        camera_data = None

        if self.__NO_CAM_FOUND:
            print(f"CameraResearcher not found {cam_type} in system")
            return camera_data

        try:
            camera_data = self._camera_stacks_by_group[cam_type].pop()
            print(f"Sucess!")
        except IndexError:
            print(f"You get all possible {cam_type}")

        return camera_data


def main():
    Resercher = CameraResearcher(
        config_path="reference/base_cam_in_company.json", visualize=False
    )

    if cam := Resercher.get_camera("cam"):
        print(f"Using camera: {cam['name']}")
        print(f"Resolution: {cam['cam_param']['width']}x{cam['cam_param']['height']}")

    if cam := Resercher.get_camera("termal"):
        print(f"Using camera: {cam['name']}")
        print(f"Resolution: {cam['cam_param']['width']}x{cam['cam_param']['height']}")


if __name__ == "__main__":
    main()
