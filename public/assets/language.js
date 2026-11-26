(() => {
  "use strict";

  const select = document.getElementById("ipe-lang-select");
  const language = window.IpeLang;
  if (!select || !language) return;

  function remember(code) {
    try {
      localStorage.setItem("ipe_lang", code);
    } catch {
      // 저장 공간이 막혀 있어도 페이지는 이동한다.
    }
  }

  function destination(option) {
    const url = new URL(option.value, location.origin);
    url.search = location.search;
    url.searchParams.delete("lang");
    url.hash = location.hash;
    return url.href;
  }

  select.addEventListener("change", (event) => {
    event.stopImmediatePropagation();
    const option = select.selectedOptions[0];
    remember(option.lang);
    location.assign(destination(option));
  }, true);

  if (!document.documentElement.hasAttribute("data-language-entry")) return;
  if (/bot|crawl|spider|slurp|bingpreview|facebookexternalhit|lighthouse|pagespeed|preview/i.test(navigator.userAgent)) return;

  const params = new URLSearchParams(location.search);
  const query = params.get("lang");
  const explicit = language.resolve(query);
  const valid = explicit !== "en" || /^en(?:[-_]|$)/i.test((query || "").trim());
  if (valid) remember(explicit);
  const detected = language.pick(navigator.languages?.length ? navigator.languages : [navigator.language]);
  const preferred = valid ? explicit : (params.has("lang") ? detected : (language.stored() || detected));
  const option = Array.from(select.options).find((item) => item.lang === preferred);
  if (option && option.lang !== select.selectedOptions[0].lang) location.replace(destination(option));
})();
