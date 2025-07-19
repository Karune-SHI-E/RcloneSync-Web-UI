async function fetchRemotes() {
  let res = await fetch('/api/remotes');
  let data = await res.json();
  let ul = document.getElementById('remote-list');
  ul.innerHTML = '';
  data.remotes.forEach(r => {
    let li = document.createElement('li');
    li.textContent = r;
    ul.appendChild(li);
  });
}

async function fetchConf() {
  let res = await fetch('/api/conf');
  let data = await res.json();
  document.getElementById('conf-editor').value = data.conf;
}

async function saveConf() {
  let content = document.getElementById('conf-editor').value;
  let res = await fetch('/api/conf', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({conf: content})
  });
  let data = await res.json();
  alert(data.status === 'ok' ? '配置保存成功' : '保存失败');
  await fetchRemotes();
}

let logPolling = false;
async function startTransfer() {
  if(logPolling){
    alert('已有传输任务进行中，请稍候');
    return;
  }
  let src_remote = document.getElementById('src-remote').value.trim();
  let src_path = document.getElementById('src-path').value.trim() || '/';
  let dst_remote = document.getElementById('dst-remote').value.trim();
  let dst_path = document.getElementById('dst-path').value.trim() || '/';
  let mode = document.getElementById('mode').value;

  if (!src_remote || !dst_remote) {
    alert('源远程和目标远程不能为空');
    return;
  }

  let res = await fetch('/api/transfer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({src_remote, src_path, dst_remote, dst_path, mode})
  });
  let data = await res.json();
  if(data.status !== 'ok'){
    alert(data.message || '启动传输失败');
    return;
  }

  let logElem = document.getElementById('transfer-log');
  logElem.textContent = '';
  logPolling = true;

  // 轮询日志接口
  (async function pollLog(){
    if(!logPolling) return;
    let res = await fetch('/api/log');
    let data = await res.json();
    logElem.textContent += data.log;
    logElem.scrollTop = logElem.scrollHeight;
    if(data.done){
      logPolling = false;
      return;
    }
    setTimeout(pollLog, 1000);
  })();

window.onload = () => {
  fetchRemotes();
  fetchConf();
};
