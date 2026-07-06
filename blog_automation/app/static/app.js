/* 블로그 자동화 스튜디오 — 프론트엔드 */

const $ = (sel) => document.querySelector(sel);

let currentPost = null; // 마지막으로 생성된 원고 (blocks 포함)

// ---------------------------------------------------------------------------
// 초기화
// ---------------------------------------------------------------------------

async function init() {
  const [cats, health] = await Promise.all([
    fetch("/api/categories").then((r) => r.json()),
    fetch("/api/health").then((r) => r.json()),
  ]);

  $("#category").innerHTML = cats
    .map((c) => `<option value="${c.id}">${c.label}</option>`)
    .join("");

  const dot = (on) => `<span class="${on ? "on" : "off"}">●</span>`;
  $("#health").innerHTML = `
    <span>${dot(health.claude_api)} Claude API ${health.claude_api ? "연결됨" : "미설정(템플릿 모드)"}</span>
    <span>${dot(health.sessions.naver)} 네이버 세션</span>
    <span>${dot(health.sessions.tistory)} 티스토리 세션</span>`;

  document.querySelectorAll('input[name="imageMode"]').forEach((el) =>
    el.addEventListener("change", () =>
      $("#folderRow").classList.toggle("hidden", el.value !== "folder" || !el.checked)
    )
  );
}

// ---------------------------------------------------------------------------
// 원고 생성
// ---------------------------------------------------------------------------

$("#btnGenerate").addEventListener("click", async () => {
  const keyword = $("#keyword").value.trim();
  if (!keyword) return setStatus("#genStatus", "키워드를 입력해 주세요.", "err");

  setStatus("#genStatus", "원고를 생성하는 중입니다…", "busy");
  $("#btnGenerate").disabled = true;

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keyword,
        category: $("#category").value,
        length: $("#length").value,
        extra_note: $("#extra").value.trim(),
        image_mode: document.querySelector('input[name="imageMode"]:checked').value,
        image_folder: $("#imageFolder").value.trim(),
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);

    currentPost = await res.json();
    currentPost.keyword = keyword;
    renderPreview();
    setStatus(
      "#genStatus",
      currentPost.engine === "claude"
        ? "✅ Claude 가 원고를 생성했습니다."
        : "✅ 템플릿 원고가 생성되었습니다. (ANTHROPIC_API_KEY 설정 시 AI 원고로 업그레이드)",
      "ok"
    );
    setPublishEnabled(true);
  } catch (e) {
    setStatus("#genStatus", "생성 실패: " + e.message, "err");
  } finally {
    $("#btnGenerate").disabled = false;
  }
});

function renderPreview() {
  $("#engineBadge").textContent =
    currentPost.engine === "claude" ? "AI 생성" : "템플릿 생성";
  $("#engineBadge").classList.remove("hidden");
  const titleInput = $("#postTitle");
  titleInput.value = currentPost.title;
  titleInput.classList.remove("hidden");
  $("#tags").innerHTML = (currentPost.tags || [])
    .map((t) => `<span>#${t}</span>`)
    .join("");
  $("#previewBody").innerHTML = currentPost.html;
}

// 제목 수정 시 반영
$("#postTitle").addEventListener("change", () => {
  if (currentPost) currentPost.title = $("#postTitle").value;
});

// ---------------------------------------------------------------------------
// 발행 / 내보내기
// ---------------------------------------------------------------------------

function setPublishEnabled(on) {
  ["#btnNaver", "#btnTistory", "#btnCopy", "#btnCopyText", "#btnExport"].forEach(
    (s) => ($(s).disabled = !on)
  );
}

async function publish(platform) {
  if (!currentPost) return;
  setStatus("#pubStatus", `${platform === "naver" ? "네이버" : "티스토리"}에 발행 중… (최대 1~2분)`, "busy");
  try {
    // 발행에는 로컬 파일 경로를 사용하도록 이미지 src 를 치환
    const blocks = currentPost.blocks.map((b) =>
      b.type === "image" && b.local_path ? { ...b, src: b.local_path } : b
    );
    const res = await fetch("/api/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        platform,
        title: currentPost.title,
        blocks,
        html: currentPost.html,
        tags: currentPost.tags,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    setStatus("#pubStatus", `✅ 발행 완료! ${data.url || ""}`, "ok");
  } catch (e) {
    setStatus("#pubStatus", "발행 실패: " + e.message, "err");
  }
}

$("#btnNaver").addEventListener("click", () => publish("naver"));
$("#btnTistory").addEventListener("click", () => publish("tistory"));

$("#btnCopy").addEventListener("click", async () => {
  if (!currentPost) return;
  try {
    // 서식 유지 복사(HTML) — 에디터에 붙여넣으면 볼드/형광펜이 유지됨
    const blob = new Blob([currentPost.html], { type: "text/html" });
    await navigator.clipboard.write([
      new ClipboardItem({ "text/html": blob, "text/plain": new Blob([currentPost.plain_text], { type: "text/plain" }) }),
    ]);
    setStatus("#pubStatus", "✅ 서식 포함 HTML이 복사되었습니다. 블로그 에디터에 붙여넣으세요.", "ok");
  } catch {
    await navigator.clipboard.writeText(currentPost.html);
    setStatus("#pubStatus", "✅ HTML 소스가 복사되었습니다.", "ok");
  }
});

$("#btnCopyText").addEventListener("click", async () => {
  if (!currentPost) return;
  await navigator.clipboard.writeText(currentPost.plain_text);
  setStatus("#pubStatus", "✅ 텍스트가 복사되었습니다.", "ok");
});

$("#btnExport").addEventListener("click", async () => {
  if (!currentPost) return;
  const res = await fetch("/api/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: currentPost.title,
      blocks: currentPost.blocks,
      keyword: currentPost.keyword,
      sub_keywords: currentPost.sub_keywords || [],
      highlight_color: currentPost.highlight_color,
      tags: currentPost.tags,
    }),
  });
  const data = await res.json();
  setStatus("#pubStatus", `✅ 저장됨: ${data.path}`, "ok");
});

// ---------------------------------------------------------------------------

function setStatus(sel, msg, cls) {
  const el = $(sel);
  el.textContent = msg;
  el.className = "status " + (cls || "");
}

init();
