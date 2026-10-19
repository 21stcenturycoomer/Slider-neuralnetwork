// ==UserScript==
// @name         Captcha Auto (授权站点，预测驱动自动滑动)
// @namespace    http://localhost/
// @version      0.1
// @description  仅在你自己的站点/授权测试站点使用，调用本地模型并自动滑动
// @match        http://localhost:5000/*
// @match        https://your-test-domain.example/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// ==/UserScript==

(function () {
  'use strict';

  const PRED_URL = 'http://localhost:9000/predict';

  function getImageData(node) {
    if (!node) return null;
    const style = node.style && node.style.backgroundImage;
    if (style && style.includes('data:image')) {
      const match = style.match(/data:image\/[^;]+;base64,([^\")]+)/);
      if (match) return match[1];
    }
    const img = node.querySelector && node.querySelector('img');
    if (img && img.src && img.src.startsWith('data:image')) return img.src.split(',')[1];
    const canvas = node.querySelector && node.querySelector('canvas');
    if (canvas && canvas.toDataURL) return canvas.toDataURL().split(',')[1];
    return null;
  }

  function predict(image_b64, cb) {
    GM_xmlhttpRequest({
      method: 'POST',
      url: PRED_URL,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ image_b64 }),
      onload: function (res) {
        try {
          const json = JSON.parse(res.responseText);
          cb(null, json);
        } catch (e) {
          cb(e);
        }
      },
      onerror: function (err) {
        cb(err);
      }
    });
  }

  function setSliderValue(ratio) {
    const slider = document.querySelector('input[type="range"]#t-slider');
    if (slider) {
      const min = Number(slider.min || 0);
      const max = Number(slider.max || 100);
      const value = min + ratio * (max - min);
      slider.value = value;
      slider.dispatchEvent(new Event('input', { bubbles: true }));
      slider.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }
    return false;
  }

  function doAutoSolve() {
    const captchaNode = document.querySelector('#t-task');
    const image_b64 = getImageData(captchaNode);
    if (!image_b64) {
      console.warn('自动脚本：未找到 captcha 图片');
      return;
    }

    predict(image_b64, function (err, result) {
      if (err) {
        console.warn('预测失败', err);
        return;
      }
      const pred = Number(result.pred || 0.5);
      const conf = Number(result.confidence || 0.0);

      console.log('预测结果', pred, 'confidence', conf);

      if (conf < 0.6) {
        console.warn('置信度过低，跳过自动提交');
        return;
      }

      setSliderValue(pred);
    });
  }

  setTimeout(function () {
    const btn = document.createElement('button');
    btn.textContent = 'Auto Solve (测试)';
    btn.style.position = 'fixed';
    btn.style.right = '20px';
    btn.style.bottom = '20px';
    btn.style.zIndex = '999999';
    btn.onclick = doAutoSolve;
    document.body.appendChild(btn);
  }, 1500);

})();
