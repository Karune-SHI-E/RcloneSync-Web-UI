import os
import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

# 1. 自动判断系统类型，确定 rclone.conf 路径
if os.name == 'nt':
    RCLONE_CONF = os.path.expandvars(r'%USERPROFILE%\.config\rclone\rclone.conf')
else:
    RCLONE_CONF = os.path.expanduser('~/.config/rclone/rclone.conf')

# 2. 确保配置文件目录存在
def ensure_conf_path():
    conf_dir = os.path.dirname(RCLONE_CONF)
    os.makedirs(conf_dir, exist_ok=True)

# 3. 读取 rclone 配置文件内容
def read_conf():
    if not os.path.exists(RCLONE_CONF):
        return ''
    try:
        with open(RCLONE_CONF, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[read_conf] 读取失败: {e}")
        return ''

# 4. 写入 rclone 配置文件（覆盖原内容）
def write_conf(content):
    try:
        ensure_conf_path()
        with open(RCLONE_CONF, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[write_conf] 写入失败: {e}")
        return False

# 5. 列出 rclone 当前配置的远程名称
def list_remotes():
    try:
        out = subprocess.check_output(['rclone', 'listremotes'], text=True)
        remotes = [r.strip(':') for r in out.strip().splitlines() if r.strip()]
        return remotes
    except subprocess.CalledProcessError as e:
        print(f"[list_remotes] rclone 调用失败: {e}")
        return []
    except FileNotFoundError:
        print("[list_remotes] rclone 未安装或未在环境变量中")
        return []
    except Exception as e:
        print(f"[list_remotes] 其他错误: {e}")
        return []

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/remotes')
def api_remotes():
    remotes = list_remotes()
    return jsonify({'remotes': remotes})

@app.route('/api/conf', methods=['GET', 'POST'])
def api_conf():
    if request.method == 'GET':
        content = read_conf()
        return jsonify({'conf': content})
    else:
        data = request.json
        content = data.get('conf', '')
        success = write_conf(content)
        return jsonify({'status': 'ok' if success else 'error'})

# 管理运行中的 rclone 进程和日志缓存
running_process = None
log_buffer = []

def clear_log_buffer():
    global log_buffer
    log_buffer = []

@app.route('/api/transfer', methods=['POST'])
def api_transfer():
    """
    启动云对云复制或同步任务。
    mode: copy 或 sync
    """
    global running_process, log_buffer

    if running_process and running_process.poll() is None:
        return jsonify({'status': 'error', 'message': '已有任务运行中，请稍后。'})

    data = request.json
    src_remote = data.get('src_remote')
    src_path = data.get('src_path', '')
    dst_remote = data.get('dst_remote')
    dst_path = data.get('dst_path', '')
    mode = data.get('mode', 'copy')  # copy 或 sync

    if not all([src_remote, dst_remote]):
        return jsonify({'status': 'error', 'message': '必须指定源和目标远程'})

    # 组装命令
    src = f'{src_remote}:{src_path}'
    dst = f'{dst_remote}:{dst_path}'
    cmd = ['rclone', mode, src, dst, '--progress', '--stats=1s']

    try:
        running_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        clear_log_buffer()
        return jsonify({'status': 'ok', 'message': f'{mode}任务已启动'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'启动任务失败: {e}'})

@app.route('/api/log')
def api_log():
    global running_process
    if not running_process:
        return jsonify({'done': True, 'log': ''})
    output = []
    while True:
        line = running_process.stdout.readline()
        if line:
            output.append(line)
        else:
            break
    done = (running_process.poll() is not None)
    return jsonify({'done': done, 'log': ''.join(output)})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """
    停止当前运行的任务
    """
    global running_process

    if not running_process or running_process.poll() is not None:
        return jsonify({'status': 'error', 'message': '当前没有运行中的任务'})

    try:
        running_process.terminate()
        running_process.wait(timeout=5)
        return jsonify({'status': 'ok', 'message': '任务已停止'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'停止任务失败: {e}'})

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    print(f'Using rclone.conf: {RCLONE_CONF}')
    app.run(host='0.0.0.0', port=5000, debug=True)

