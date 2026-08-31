const translations = Object.freeze({
  en: Object.freeze({
    metaTitle: 'FaceLogix | Attendance, verified',
    metaDescription: 'FaceLogix is a self-hosted face-recognition attendance system with liveness checks, private biometric processing, and complete operations tooling.',
    ogDescription: 'A self-hosted attendance system that verifies the person, records the event, and keeps biometric processing under your control.',
    skipLink: 'Skip to content',
    primaryNavigation: 'Primary navigation',
    homeLabel: 'FaceLogix home',
    pageSections: 'Page sections',
    mobilePageSections: 'Mobile page sections',
    languageLabel: 'Language',
    navWorkflow: 'Workflow',
    navArchitecture: 'Architecture',
    navPrivacy: 'Privacy',
    viewGithub: 'View on GitHub',
    menu: 'Menu',
    heroTitle: 'Attendance, verified.',
    heroBody: 'FaceLogix gives operations teams self-hosted employee check-ins and check-outs with liveness checks and controlled biometric processing.',
    inspectWorkflow: 'Inspect the workflow',
    verificationSequence: 'Illustrative FaceLogix verification sequence',
    verificationRecord: 'Verification record',
    illustrativeSequence: 'Illustrative sequence',
    liveness: 'LIVENESS',
    quality: 'QUALITY',
    match: 'MATCH',
    workflowTitle: 'One arrival. Three accountable steps.',
    workflowBody: 'Every check-in moves through the same explicit path, from capture to a reportable attendance event.',
    capture: 'Capture',
    captureTitle: 'Confirm a usable face',
    captureBody: 'Image-quality checks reject poor captures before recognition begins.',
    verify: 'Verify',
    verifyTitle: 'Test liveness and identity',
    verifyBody: 'Internal ONNX models detect spoofing and compare the face embedding.',
    record: 'Record',
    recordTitle: 'Write the attendance event',
    recordBody: 'A successful check becomes an organization-scoped check-in or check-out.',
    architectureTitle: 'A deployment boundary you can explain.',
    architectureBody: 'The web app, API, face inference, and PostgreSQL database ship as one coherent Docker Compose deployment behind your own TLS edge.',
    deploymentGuide: 'Read the deployment guide',
    systemArchitecture: 'FaceLogix system architecture',
    device: 'Device',
    devicePlatforms: 'Desktop, tablet, mobile',
    sameOrigin: 'Same origin',
    application: 'Application',
    applicationFunctions: 'Auth, roles, attendance',
    inference: 'Inference',
    inferenceFunctions: 'Detection, match, liveness',
    state: 'State',
    stateFunctions: 'pgvector and records',
    privacyTitle: 'Images in. Embeddings out.',
    privacyBody: 'Enrollment images are converted to face embeddings and are not retained.',
    enrollmentDataFlow: 'Face enrollment data flow',
    enrollmentInput: 'Enrollment input',
    inputChecks: 'Quality and liveness checked',
    transform: 'Transform',
    storedRepresentation: 'Stored representation',
    faceEmbedding: 'Face embedding',
    organizationScoped: 'Organization scoped',
    sourceImage: 'Source image',
    notRetained: 'Not retained',
    operationsTitle: 'Built around the whole attendance loop.',
    operationsBody: 'From initial enrollment to exports, the operational tools live beside the verification system.',
    people: 'People',
    peopleTitle: 'Organization-scoped access',
    peopleBody: 'Users, roles, profiles, and elevated-account safeguards.',
    enrollment: 'Enrollment',
    enrollmentTitle: 'Atomic bulk import',
    enrollmentBody: 'Preview up to 100 people, resolve conflicts, then commit once.',
    devices: 'Devices',
    devicesTitle: 'Revocable credentials',
    devicesBody: 'Provision attendance devices without permanent shared secrets.',
    records: 'Records',
    recordsTitle: 'Check-in and check-out',
    recordsBody: 'Review attendance across the organization and individual people.',
    reporting: 'Reporting',
    reportingTitle: 'Spreadsheet-ready exports',
    reportingBody: 'Export attendance as CSV for downstream reporting workflows.',
    closingTitle: 'Inspect every layer.',
    closingBody: 'FaceLogix is MIT licensed. Review the architecture, deployment scripts, inference pipeline, and application code on GitHub.',
    openRepository: 'Open the repository',
    footerTagline: 'Self-hosted attendance verification.',
    license: 'MIT License',
    readyTitle: 'Ready to verify',
    readyDetail: 'No image retained',
    runCheck: 'Run check',
    verifying: 'Verifying',
    checkingLiveness: 'Checking liveness',
    processing: 'Processing inside FaceLogix',
    runAgain: 'Run again',
    recordedTitle: 'Attendance recorded',
    recordedDetail: 'Source image not retained',
    canvasIdle: 'LANDMARK TRACE',
    canvasVerified: 'MATCH CONFIRMED',
    canvasLocal: 'LOCAL INFERENCE'
  }),
  vi: Object.freeze({
    metaTitle: 'FaceLogix | Chấm công đã xác thực',
    metaDescription: 'FaceLogix là hệ thống chấm công nhận diện khuôn mặt tự lưu trữ, có kiểm tra người thật, xử lý sinh trắc học riêng tư và đầy đủ công cụ vận hành.',
    ogDescription: 'Hệ thống chấm công tự lưu trữ giúp xác thực nhân sự, ghi nhận sự kiện và giữ xử lý sinh trắc học trong quyền kiểm soát của bạn.',
    skipLink: 'Chuyển đến nội dung chính',
    primaryNavigation: 'Điều hướng chính',
    homeLabel: 'Trang chủ FaceLogix',
    pageSections: 'Các phần trên trang',
    mobilePageSections: 'Các phần trên trang cho di động',
    languageLabel: 'Ngôn ngữ',
    navWorkflow: 'Quy trình',
    navArchitecture: 'Kiến trúc',
    navPrivacy: 'Quyền riêng tư',
    viewGithub: 'Xem trên GitHub',
    menu: 'Trình đơn',
    heroTitle: 'Chấm công, đã xác thực.',
    heroBody: 'FaceLogix cung cấp cho đội ngũ vận hành hệ thống chấm công tự triển khai, xác thực lượt vào và ra bằng kiểm tra người thật và xử lý sinh trắc học do bạn kiểm soát.',
    inspectWorkflow: 'Xem quy trình',
    verificationSequence: 'Trình tự xác thực minh họa của FaceLogix',
    verificationRecord: 'Bản ghi xác thực',
    illustrativeSequence: 'Trình tự minh họa',
    liveness: 'NGƯỜI THẬT',
    quality: 'CHẤT LƯỢNG',
    match: 'ĐỐI CHIẾU',
    workflowTitle: 'Một lượt chấm công. Ba bước rõ ràng.',
    workflowBody: 'Mỗi lượt chấm công đi qua cùng một quy trình minh bạch, từ thu nhận đến bản ghi có thể báo cáo.',
    capture: 'Thu nhận',
    captureTitle: 'Xác nhận khuôn mặt đạt yêu cầu',
    captureBody: 'Kiểm tra chất lượng loại bỏ ảnh không đạt trước khi bắt đầu nhận diện.',
    verify: 'Xác thực',
    verifyTitle: 'Kiểm tra người thật và danh tính',
    verifyBody: 'Các mô hình ONNX nội bộ phát hiện giả mạo và so sánh vector đặc trưng khuôn mặt.',
    record: 'Ghi nhận',
    recordTitle: 'Ghi sự kiện chấm công',
    recordBody: 'Một lần xác thực thành công trở thành lượt vào hoặc ra trong phạm vi tổ chức.',
    architectureTitle: 'Một ranh giới triển khai rõ ràng.',
    architectureBody: 'Ứng dụng web, API, suy luận khuôn mặt và cơ sở dữ liệu PostgreSQL được triển khai đồng bộ bằng Docker Compose sau lớp TLS của bạn.',
    deploymentGuide: 'Đọc hướng dẫn triển khai',
    systemArchitecture: 'Kiến trúc hệ thống FaceLogix',
    device: 'Thiết bị',
    devicePlatforms: 'Máy tính, máy tính bảng, di động',
    sameOrigin: 'Cùng nguồn',
    application: 'Ứng dụng',
    applicationFunctions: 'Xác thực, vai trò, chấm công',
    inference: 'Suy luận',
    inferenceFunctions: 'Phát hiện, đối chiếu, người thật',
    state: 'Dữ liệu',
    stateFunctions: 'pgvector và bản ghi',
    privacyTitle: 'Ảnh vào. Vector ra.',
    privacyBody: 'Ảnh đăng ký được chuyển thành vector đặc trưng khuôn mặt và không được lưu lại.',
    enrollmentDataFlow: 'Luồng dữ liệu đăng ký khuôn mặt',
    enrollmentInput: 'Đầu vào đăng ký',
    inputChecks: 'Đã kiểm tra chất lượng và người thật',
    transform: 'Chuyển đổi',
    storedRepresentation: 'Dữ liệu được lưu',
    faceEmbedding: 'Vector khuôn mặt',
    organizationScoped: 'Trong phạm vi tổ chức',
    sourceImage: 'Ảnh nguồn',
    notRetained: 'Không được lưu',
    operationsTitle: 'Bao quát toàn bộ vòng đời chấm công.',
    operationsBody: 'Từ đăng ký ban đầu đến xuất dữ liệu, các công cụ vận hành luôn đi cùng hệ thống xác thực.',
    people: 'Nhân sự',
    peopleTitle: 'Phân quyền theo tổ chức',
    peopleBody: 'Người dùng, vai trò, hồ sơ và biện pháp bảo vệ tài khoản đặc quyền.',
    enrollment: 'Đăng ký',
    enrollmentTitle: 'Nhập hàng loạt: tất cả hoặc không',
    enrollmentBody: 'Xem trước tối đa 100 người, xử lý xung đột và chỉ ghi nhận khi tất cả đều hợp lệ; bất kỳ lỗi nào cũng hủy toàn bộ lượt nhập.',
    devices: 'Thiết bị',
    devicesTitle: 'Thông tin xác thực có thể thu hồi',
    devicesBody: 'Cấp quyền cho thiết bị chấm công mà không dùng bí mật dùng chung vĩnh viễn.',
    records: 'Bản ghi',
    recordsTitle: 'Chấm công vào và ra',
    recordsBody: 'Xem dữ liệu chấm công của toàn tổ chức và từng nhân sự.',
    reporting: 'Báo cáo',
    reportingTitle: 'Xuất dữ liệu sẵn cho bảng tính',
    reportingBody: 'Xuất dữ liệu chấm công dạng CSV cho các quy trình báo cáo tiếp theo.',
    closingTitle: 'Kiểm tra từng lớp.',
    closingBody: 'FaceLogix dùng giấy phép MIT. Xem kiến trúc, kịch bản triển khai, luồng suy luận và mã nguồn ứng dụng trên GitHub.',
    openRepository: 'Mở kho mã nguồn',
    footerTagline: 'Xác thực chấm công tự lưu trữ.',
    license: 'Giấy phép MIT',
    readyTitle: 'Sẵn sàng xác thực',
    readyDetail: 'Không lưu ảnh',
    runCheck: 'Chạy kiểm tra',
    verifying: 'Đang xác thực',
    checkingLiveness: 'Đang kiểm tra người thật',
    processing: 'Xử lý bên trong FaceLogix',
    runAgain: 'Chạy lại',
    recordedTitle: 'Đã ghi nhận chấm công',
    recordedDetail: 'Không lưu ảnh nguồn',
    canvasIdle: 'MỐC KHUÔN MẶT',
    canvasVerified: 'ĐÃ ĐỐI CHIẾU',
    canvasLocal: 'SUY LUẬN CỤC BỘ'
  })
});

const supportedLocales = new Set(Object.keys(translations));
const canvas = document.querySelector('#face-trace');
const stage = document.querySelector('.verification-stage');
const verifyButton = document.querySelector('#verify-button');
const verificationTitle = document.querySelector('#verification-title');
const verificationDetail = document.querySelector('#verification-detail');
const stateIndex = document.querySelector('.state-index');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const textElements = document.querySelectorAll('[data-i18n]');
const ariaElements = document.querySelectorAll('[data-i18n-aria-label]');
const languageButtons = document.querySelectorAll('[data-language]');

const ctx = canvas?.getContext('2d');
const facePath = new Path2D();
const featurePath = new Path2D();
const measurementPath = new Path2D();
const anchors = Object.freeze([
  [360, 76], [246, 110], [202, 314], [250, 472], [360, 552],
  [470, 472], [518, 314], [474, 110], [282, 267], [438, 267],
  [360, 374], [306, 420], [414, 420]
]);

let currentLocale = 'en';
let verificationState = 'idle';

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

function message(key) {
  return translations[currentLocale][key] ?? translations.en[key] ?? key;
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

  for (const [x, y] of anchors) {
    ctx.beginPath();
    ctx.rect(x - 4, y - 4, 8, 8);
    ctx.fill();
    ctx.stroke();
  }

  ctx.restore();

  ctx.fillStyle = '#33413c';
  ctx.font = '700 13px "Cascadia Mono", monospace';
  ctx.fillText(verified ? message('canvasVerified') : message('canvasIdle'), 28, 42);
  ctx.font = '500 11px "Cascadia Mono", monospace';
  ctx.fillText(message('canvasLocal'), 28, 61);
}

function renderVerificationCopy() {
  if (!verifyButton || !verificationTitle || !verificationDetail) return;

  if (verificationState === 'scanning') {
    verifyButton.textContent = message('verifying');
    verificationTitle.textContent = message('checkingLiveness');
    verificationDetail.textContent = message('processing');
    return;
  }

  if (verificationState === 'verified') {
    verifyButton.textContent = message('runAgain');
    verificationTitle.textContent = message('recordedTitle');
    verificationDetail.textContent = message('recordedDetail');
    return;
  }

  verifyButton.textContent = message('runCheck');
  verificationTitle.textContent = message('readyTitle');
  verificationDetail.textContent = message('readyDetail');
}

function applyLocale(locale, updateUrl = false) {
  currentLocale = supportedLocales.has(locale) ? locale : 'en';
  const activeMessages = translations[currentLocale];

  document.documentElement.lang = currentLocale;
  document.title = activeMessages.metaTitle;
  document.querySelector('meta[name="description"]')?.setAttribute('content', activeMessages.metaDescription);
  document.querySelector('meta[property="og:title"]')?.setAttribute('content', activeMessages.metaTitle);
  document.querySelector('meta[property="og:description"]')?.setAttribute('content', activeMessages.ogDescription);

  for (const element of textElements) {
    const key = element.dataset.i18n;
    if (key && activeMessages[key]) element.textContent = activeMessages[key];
  }

  for (const element of ariaElements) {
    const key = element.dataset.i18nAriaLabel;
    if (key && activeMessages[key]) element.setAttribute('aria-label', activeMessages[key]);
  }

  for (const button of languageButtons) {
    button.setAttribute('aria-pressed', String(button.dataset.language === currentLocale));
  }

  renderVerificationCopy();
  renderTrace();

  try {
    window.localStorage.setItem('facelogix-language', currentLocale);
  } catch {
    // Language selection still works when storage is unavailable.
  }

  if (updateUrl) {
    const url = new URL(window.location.href);
    if (currentLocale === 'vi') url.searchParams.set('lang', 'vi');
    else url.searchParams.delete('lang');
    window.history.replaceState({}, '', url);
  }
}

function initialLocale() {
  const parameterLocale = new URL(window.location.href).searchParams.get('lang');
  if (parameterLocale && supportedLocales.has(parameterLocale)) return parameterLocale;

  try {
    const storedLocale = window.localStorage.getItem('facelogix-language');
    if (storedLocale && supportedLocales.has(storedLocale)) return storedLocale;
  } catch {
    // Fall through to the browser language.
  }

  return window.navigator.language.toLowerCase().startsWith('vi') ? 'vi' : 'en';
}

function runVerification() {
  if (!stage || !verifyButton || !stateIndex) return;

  stage.classList.remove('is-verified');
  stage.classList.remove('is-scanning');
  void stage.offsetWidth;
  stage.classList.add('is-scanning');

  verificationState = 'scanning';
  verifyButton.disabled = true;
  stateIndex.textContent = 'B';
  renderVerificationCopy();
  renderTrace(false);

  const delay = reducedMotion.matches ? 120 : 1850;
  window.setTimeout(() => {
    stage.classList.remove('is-scanning');
    stage.classList.add('is-verified');
    verificationState = 'verified';
    verifyButton.disabled = false;
    stateIndex.textContent = 'C';
    renderVerificationCopy();
    renderTrace(true);
  }, delay);
}

if (canvas && ctx) {
  const resizeObserver = new ResizeObserver(() => renderTrace());
  resizeObserver.observe(canvas);
}

for (const button of languageButtons) {
  button.addEventListener('click', () => {
    const locale = button.dataset.language;
    if (!locale) return;
    const mobileMenu = button.closest('details');
    applyLocale(locale, true);
    mobileMenu?.removeAttribute('open');
    mobileMenu?.querySelector('summary')?.focus();
  });
}

verifyButton?.addEventListener('click', runVerification);

document.querySelectorAll('.mobile-menu a').forEach((link) => {
  link.addEventListener('click', () => {
    link.closest('details')?.removeAttribute('open');
  });
});

applyLocale(initialLocale());
