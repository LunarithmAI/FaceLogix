const canvas = document.querySelector('#face-trace');
const stage = document.querySelector('.verification-stage');
const verifyButton = document.querySelector('#verify-button');
const verificationTitle = document.querySelector('#verification-title');
const verificationDetail = document.querySelector('#verification-detail');
const stateIndex = document.querySelector('.state-index');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

const ctx = canvas?.getContext('2d');
const facePath = new Path2D();
const featurePath = new Path2D();
const measurementPath = new Path2D();

facePath.moveTo(360, 76);
facePath.bezierCurveTo(246, 74, 186, 172, 202, 314);
facePath.bezierCurveTo(214, 432, 278, 520, 360, 552);
facePath.bezierCurveTo(442, 520, 506, 432, 518, 314);
facePath.bezierCurveTo(534, 172, 474, 74, 360, 76);

featurePath.moveTo(264, 250);
featurePath.bezierCurveTo(295, 228, 328, 231, 345, 249);
featurePath.moveTo(375, 249);
featurePath.bezierCurveTo(392, 231, 425, 228, 456, 250);
featurePath.moveTo(282, 267);
featurePath.bezierCurveTo(306, 279, 326, 279, 344, 265);
featurePath.moveTo(376, 265);
featurePath.bezierCurveTo(394, 279, 414, 279, 438, 267);
featurePath.moveTo(360, 270);
featurePath.bezierCurveTo(347, 332, 342, 361, 360, 374);
featurePath.bezierCurveTo(372, 376, 382, 372, 390, 365);
featurePath.moveTo(306, 420);
featurePath.bezierCurveTo(340, 444, 380, 444, 414, 420);
featurePath.bezierCurveTo(380, 410, 340, 410, 306, 420);

for (let y = 128; y <= 500; y += 62) {
  const inset = Math.abs(y - 314) * 0.22;
  measurementPath.moveTo(218 + inset, y);
  measurementPath.bezierCurveTo(292, y + 14, 428, y - 14, 502 - inset, y);
}

for (let x = 252; x <= 468; x += 54) {
  measurementPath.moveTo(x, 118);
  measurementPath.bezierCurveTo(x - 28, 240, x + 28, 382, x, 506);
}

function renderTrace(verified = stage?.classList.contains('is-verified')) {
  if (!ctx || !canvas) return;

  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.round(rect.width * ratio));
  const height = Math.max(1, Math.round(rect.height * ratio));

  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  ctx.setTransform(width / 720, 0, 0, height / 620, 0, 0);
  ctx.clearRect(0, 0, 720, 620);

  ctx.fillStyle = '#e5eae8';
  ctx.fillRect(0, 0, 720, 620);

  ctx.save();
  ctx.strokeStyle = verified ? '#0b7446' : '#1e5bff';
  ctx.lineWidth = 1.2;
  ctx.globalAlpha = 0.34;
  ctx.stroke(measurementPath);
  ctx.restore();

  ctx.save();
  ctx.strokeStyle = '#111715';
  ctx.lineWidth = 2.2;
  ctx.stroke(facePath);
  ctx.lineWidth = 1.5;
  ctx.stroke(featurePath);
  ctx.restore();

  ctx.save();
  ctx.strokeStyle = verified ? '#0b7446' : '#1e5bff';
  ctx.fillStyle = '#f2f5f4';
  ctx.lineWidth = 2;

  const anchors = [
    [360, 76], [246, 110], [202, 314], [250, 472], [360, 552],
    [470, 472], [518, 314], [474, 110], [282, 267], [438, 267],
    [360, 374], [306, 420], [414, 420]
  ];

  for (const [x, y] of anchors) {
    ctx.beginPath();
    ctx.rect(x - 4, y - 4, 8, 8);
    ctx.fill();
    ctx.stroke();
  }

  ctx.restore();

  ctx.fillStyle = '#33413c';
  ctx.font = '700 13px "Cascadia Mono", monospace';
  ctx.fillText(verified ? 'MATCH CONFIRMED' : 'LANDMARK TRACE', 28, 42);
  ctx.font = '500 11px "Cascadia Mono", monospace';
  ctx.fillText('LOCAL INFERENCE', 28, 61);
}

function runVerification() {
  if (!stage || !verifyButton || !verificationTitle || !verificationDetail || !stateIndex) return;

  stage.classList.remove('is-verified');
  stage.classList.remove('is-scanning');
  void stage.offsetWidth;
  stage.classList.add('is-scanning');

  verifyButton.disabled = true;
  verifyButton.textContent = 'Verifying';
  verificationTitle.textContent = 'Checking liveness';
  verificationDetail.textContent = 'Processing inside FaceLogix';
  stateIndex.textContent = 'B';
  renderTrace(false);

  const delay = reducedMotion.matches ? 120 : 1850;
  window.setTimeout(() => {
    stage.classList.remove('is-scanning');
    stage.classList.add('is-verified');
    verifyButton.disabled = false;
    verifyButton.textContent = 'Run again';
    verificationTitle.textContent = 'Attendance recorded';
    verificationDetail.textContent = 'Source image not retained';
    stateIndex.textContent = 'C';
    renderTrace(true);
  }, delay);
}

if (canvas && ctx) {
  const resizeObserver = new ResizeObserver(() => renderTrace());
  resizeObserver.observe(canvas);
  renderTrace();
}

verifyButton?.addEventListener('click', runVerification);

document.querySelectorAll('.mobile-menu a').forEach((link) => {
  link.addEventListener('click', () => {
    link.closest('details')?.removeAttribute('open');
  });
});
