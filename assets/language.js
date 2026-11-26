(() => {
  "use strict";

  const select = document.getElementById("ipe-lang-select");
  const language = window.IpeLang;
  if (!select || !language) return;

  function remember(code) {
    try {
      localStorage.setItem("ipe_lang", code);
    } catch {
      return false;
    }
    return language.stored() === code;
  }

  function destination(option, saved) {
    const url = new URL(option.value, location.origin);
    url.search = location.search;
    if (option.lang === "en" && !saved) {
      url.searchParams.set("lang", "en");
    } else {
      url.searchParams.delete("lang");
    }
    url.hash = location.hash;
    return url.href;
  }

  select.addEventListener("change", (event) => {
    event.stopImmediatePropagation();
    const option = select.selectedOptions[0];
    location.assign(destination(option, remember(option.lang)));
  }, true);

  if (!document.documentElement.hasAttribute("data-language-entry")) return;
  if (/bot|crawl|spider|slurp|bingpreview|facebookexternalhit|lighthouse|pagespeed|preview/i.test(navigator.userAgent)) return;

  const params = new URLSearchParams(location.search);
  const query = params.get("lang");
  const explicit = language.resolve(query);
  const valid = explicit !== "en" || /^en(?:[-_]|$)/i.test((query || "").trim());
  const saved = valid && remember(explicit);
  const detected = language.pick(navigator.languages?.length ? navigator.languages : [navigator.language]);
  const preferred = valid ? explicit : (params.has("lang") ? detected : (language.stored() || detected));
  const option = Array.from(select.options).find((item) => item.lang === preferred);
  if (option && option.lang !== select.selectedOptions[0].lang) {
    location.replace(destination(option, saved));
  } else if (valid && explicit === "en" && !saved) {
    // 영어는 경로 접두사가 없어 저장이 차단되면 내부 링크에도 선택을 전달한다.
    for (const link of document.querySelectorAll('a[href^="/"]')) {
      const url = new URL(link.href);
      if (url.origin !== location.origin) continue;
      url.searchParams.set("lang", "en");
      link.href = url.href;
    }
  }
})();
