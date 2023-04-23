# -*- encoding=utf-8 -*-
# Run Airtest in parallel on multi-device
import os
import traceback
import subprocess
import webbrowser
import time
import json
import shutil
from airtest.core.android.adb import ADB
from jinja2 import Environment, FileSystemLoader


def run(devices, air, run_all=False):
    """"
        run_all
            = True: 从头开始完整测试 (run test fully) ;
            = False: 续着data.json的进度继续测试 (continue test with the progress in data.jason)
    """
    try:
        results = load_jdon_data(air, run_all)
        tasks = run_on_multi_device(devices, air, results, run_all)
        for task in tasks:
            status = task['process'].wait()
            results['tests'][task['dev']] = run_one_report(task['air'], task['dev'])
            results['tests'][task['dev']]['status'] = status
            json.dump(results, open('data.json', "w"), indent=4)
        run_summary(results)
    except Exception as e:
        traceback.print_exc()


def run_on_multi_device(devices, air, results, run_all):
    """
        在多台设备上运行airtest脚本
        Run airtest on multi-device
    """
    tasks = []
    for dev in devices:
        if (not run_all and results['tests'].get(dev) and
           results['tests'].get(dev).get('status') == 0):
            print("Skip device %s" % dev)
            continue
        log_dir = get_log_dir(dev, air)
        cmd = [
            "airtest",
            "run",
            air,
            "--device",
            "Android:///" + dev,
            "--log",
            log_dir
        ]
        try:
            tasks.append({
                'process': subprocess.Popen(cmd, cwd=os.getcwd()),
                'dev': dev,
                'air': air
            })
        except Exception as e:
            traceback.print_exc()
    return tasks


def run_one_report(air, dev):
    """"
        生成一个脚本的测试报告
        Build one test report for one air script
    """
    try:
        log_dir = get_log_dir(dev, air)
        log = os.path.join(log_dir, 'log.txt')
        if os.path.isfile(log):
            cmd = [
                "airtest",
                "report",
                air,
                "--log_root",
                log_dir,
                "--outfile",
                os.path.join(log_dir, 'log.html'),
                "--lang",
                "zh"
            ]
            ret = subprocess.call(cmd, cwd=os.getcwd())
            return {
                    'status': ret,
                    'path': os.path.join(log_dir, 'log.html')
                    }
        else:
            print("Report build Failed. File not found in dir %s" % log)
    except Exception as e:
        traceback.print_exc()
    return {'status': -1, 'device': dev, 'path': ''}


def run_summary(data):
    """"
        生成汇总的测试报告
        Build sumary test report
    """
    try:
        summary = {
            'time': "%.3f" % (time.time() - data['start']),
            'success': [item['status'] for item in data['tests'].values()].count(0),
            'count': len(data['tests'])
        }
        summary.update(data)
        summary['start'] = time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime(data['start']))
        env = Environment(loader=FileSystemLoader(os.getcwd()),
                          trim_blocks=True)
        html = env.get_template('report_tpl.html').render(data=summary)
        with open("report.html", "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open('report.html')
    except Exception as e:
        traceback.print_exc()


def load_jdon_data(air, run_all):
    """"
        加载进度
            如果data.json存在且run_all=False，加载进度
            否则，返回一个空的进度数据
        Loading data
            if data.json exists and run_all=False, loading progress in data.json
            else return an empty data
    """
    json_file = os.path.join(os.getcwd(), 'data.json')
    if (not run_all) and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'] = time.time()
        return data
    else:
        clear_log_dir(air)
        return {
            'start': time.time(),
            'script': air,
            'tests': {}

        }


def clear_log_dir(air):
    """"
        清理log文件夹 test_blackjack.air/log
        Remove folder test_blackjack.air/log
    """
    log = os.path.join(os.getcwd(), air, 'log')
    if os.path.exists(log):
        shutil.rmtree(log)


def get_log_dir(device, air):
    """"
        在 test_blackjack.air/log/ 文件夹下创建每台设备的运行日志文件夹
        Create log folder based on device name under test_blackjack.air/log/
    """
    log_dir = os.path.join(air, 'log', device.replace(".", "_").replace(':', '_'))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir


if __name__ == '__main__':
    """
        初始化数据
        Init variables here
    """
    devices = [tmp[0] for tmp in ADB().devices()]
    air = 'test_blackjack.air'

    # Continue tests saved in data.json
    # Skip scripts that run succeed
    # 基于data.json的进度，跳过已运行成功的脚本
    # run(devices, air)

    # Resun all script
    # 重新运行所有脚本
    run(devices, air, run_all=True)
