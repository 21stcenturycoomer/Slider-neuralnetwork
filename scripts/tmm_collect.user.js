// ==UserScript==
// @name         Captcha Collector (授权站点，手动采集)
// @namespace    http://localhost/
// @version      0.1
// @description  用户在站点内手动完成验证后，采集图像 + challenge + 正确答案
// @match        http://localhost:5000/*
// @match        https://your-test-domain.example/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// ==/UserScript==

(function () {
  'use strict';

  // 采集后端地址（本地测试）
  const COLLECTOR_URL = 'http://localhost:8000/collect';

  // 尝试从节点读取 base64 图像（支持 background-image data:, <img src="data:...">, canvas）
  function getImageData(node) {
    if (!node) return null;
    const style = node.style && node.style.backgroundImage;
    if (style && style.includes('data:image')) {
      const match = style.match(/data:image\/[^;]+;base64,([^\")]+)/);
      if (match) return match[1];
    }
    const img = node.querySelector && node.querySelector('img');
    if (img && img.src && img.src.startsWith('data:image')) {
      return img.src.split(',')[1];
    }
    const canvas = node.querySelector && node.querySelector('canvas');
    if (canvas && canvas.toDataURL) {
      return canvas.toDataURL().split(',')[1];
    }
    return null;
  }

  function uploadSample() {
    const challengeEl = document.querySelector('input[name="t-challenge"], input#t-challenge');
    const responseEl = document.querySelector('input[name="t-response"], input#t-resp');
    const sliderEl = document.querySelector('input[type="range"]#t-slider');
    const captchaNode = document.querySelector('#t-task');

    const challenge = challengeEl ? challengeEl.value : null;
    const response = responseEl ? responseEl.value : (sliderEl ? sliderEl.value : null);
    const image_b64 = getImageData(captchaNode);

    const consent = confirm('允许上传本次样本（图片 + challenge + 实际答案）用于本站训练？');
    if (!consent) return;

    const payload = {
      challenge,
      response,
      image_b64,
      meta: {
        url: location.href,
        timestamp: new Date().toISOString(),
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight,
          dpr: window.devicePixelRatio
        }
      },
      consent: true
    };

    GM_xmlhttpRequest({
      method: 'POST',
      url: COLLECTOR_URL,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(payload),
      onload: function (res) {
        console.log('采集成功', res.status, res.responseText);
      },
      onerror: function (err) {
        console.warn('采集失败', err);
      }
    });
  }

  // 监听页面上任意 form 的提交，稍后触发上传（非阻塞）
  window.addEventListener('submit', function (e) {
    const form = e.target;
    if (form && form.matches('form')) {
      setTimeout(uploadSample, 100);
    }
  }, true);

})();
