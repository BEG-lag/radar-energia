/* radar·energía: search, filters, English toggle and copy buttons.
   The page is fully rendered without this script; it only adds interaction.
   No third-party code, no analytics, no cookies. */
(function () {
  "use strict";

  var EN = {
    "nav.skip": "Skip to content", "nav.today": "Today", "nav.markets": "Markets", "nav.archive": "Archive",
    "nav.sources": "Sources", "nav.lang": "Leer en español",
    "hero.kicker": "Radar for", "hero.title.a": "Mexico's energy sector today,", "hero.title.b": "with its official source.",
    "hero.sub": "What the Official Gazette (DOF) published on energy, what is new from the regulator (CNE), the ministry (SENER), ASEA and CENACE, and the day's market references. Rebuilt automatically every morning and evening; every item links to its source.",
    "hero.stat.dof": "Energy items in today's DOF", "hero.stat.week": "Items, last 7 days", "hero.radar": "Last 30 days. Angle: subsector. Distance from centre: age.", "hero.stat.total": "In the archive since", "hero.stat.fix": "FIX (MXN/USD)",
    "dof.title": "Official Gazette (DOF)", "dof.editions": "editions",
    "dof.today.none": "Today's DOF has no energy items. The most recent ones are below.",
    "dof.today.noedition": "No DOF edition today (or not published yet). The most recent items are below.",
    "dof.latest": "Latest DOF with energy items",
    "auth.title": "Regulator and ministry", "auth.none": "No recent items.",
    "auth.note": "Press releases, documents and articles of CNE, SENER, ASEA and CENACE on gob.mx. Resolutions and agreements of general scope also appear in the DOF.",
    "mk.title": "Market references", "mk.fix": "FIX exchange rate", "mk.fix.pub": "Published in the DOF on", "mk.source": "Source",
    "mk.first": "first reading", "mk.nochange": "no change", "mk.pz": "Load zone price, day-ahead market",
    "mk.pz.note": "Simple average of the 24 hourly prices for operating day", "mk.range": "hourly range",
    "mk.fuel": "Gasoline and diesel, national median",
    "mk.fuel.note": "Prices stations report to the CNE. The source keeps no history: the series starts on",
    "mk.gaslp": "LP gas, maximum prices", "mk.gaslp.note": "Official table by region and sales channel. The radar links the current PDF; it does not extract figures.",
    "mk.gaslp.all": "All weeks", "mk.manual": "Manual lookup",
    "mk.manual.note": "References that cannot be read automatically and reliably. The radar does not scrape them: here is the official link.",
    "fuel.regular": "Regular gasoline", "fuel.premium": "Premium gasoline", "fuel.diesel": "Diesel", "fuel.stations": "stations",
    "pulse.title": "Pulse by subsector", "pulse.week": "This week", "pulse.month": "This month",
    "archive.title": "Archive and search", "archive.lede": "Last 30 days. Type or filter to search the whole archive.", "archive.none": "No items.",
    "search.q": "Keyword", "search.placeholder": "natural gas, permit, NOM...", "search.ss": "Subsector", "search.ag": "Authority",
    "search.src": "Origin", "search.all": "All", "search.clear": "Clear",
    "rss.title": "Subscribe via RSS",
    "rss.p1": "RSS is an open format to follow a site without giving your email and without algorithms: your reader checks the links and shows what is new, in order.",
    "rss.p2": "Copy a link and paste it into your feed reader (Feedly, Inoreader, NetNewsWire, Thunderbird or Outlook). Every new radar item arrives with its official title and the link to the source.",
    "rss.p3": "Feeds use Atom, the standard every RSS reader understands.",
    "feed.all": "The whole radar", "feed.copy": "Copy", "feed.copied": "Copied",
    "src.title": "Verified sources", "src.evidence": "Full evidence", "src.status": "Status", "src.source": "Source", "src.use": "Use in the radar",
    "src.note": "Each source was tested without accounts or tokens, with pauses between requests and respecting robots.txt. GREEN is used automatically, YELLOW with care, RED is only linked.",
    "src.rules": "How items are classified: public keyword rules, no artificial intelligence. Each card shows which rule included it.",
    "ss.electricidad": "Electricity", "ss.hidrocarburos": "Hydrocarbons", "ss.gas-natural": "Natural gas",
    "ss.petroliferos": "Petroleum products", "ss.renovables": "Renewables", "ss.mineria": "Mining", "ss.general": "Energy (general)",
    "ed.matutina": "Morning", "ed.vespertina": "Evening", "ed.extraordinaria": "Extra", "item.rules": "rules",
    "foot.pivotek": "Legal advice in Energy and Infrastructure.",
    "foot.disclaimer": "Public information compiled automatically. Not legal advice. Only the DOF and the issuing authorities are official sources.",
    "foot.license": "Code MIT, data CC0", "w.to": "to", "foot.notrack": "No analytics, no cookies"
  };
  var PLURAL = {
    es: {
      "dof.today.count": function (n) { return n + (n === 1 ? " publicación de energía" : " publicaciones de energía"); },
      "dof.today.of": function (n) { return "de " + n + " notas revisadas"; },
      "pulse.items": function (n) { return n === 1 ? "publicación" : "publicaciones"; }
    },
    en: {
      "dof.today.count": function (n) { return n + (n === 1 ? " energy item" : " energy items"); },
      "dof.today.of": function (n) { return "out of " + n + " notes reviewed"; },
      "pulse.items": function (n) { return n === 1 ? "item" : "items"; }
    }
  };
  var LABELS = {
    es: {
      ss: { electricidad: "Electricidad", hidrocarburos: "Hidrocarburos", "gas-natural": "Gas natural", petroliferos: "Petrolíferos", renovables: "Renovables", mineria: "Minería", general: "Energía (general)" },
      ed: { matutina: "Matutina", vespertina: "Vespertina", extraordinaria: "Extra" },
      rules: "reglas", found: function (n, total) { return "<strong>" + n + "</strong> " + (n === 1 ? "resultado" : "resultados") + (total > n ? " (se muestran " + total + ")" : "") + " en todo el archivo."; },
      loading: "Cargando el archivo...", error: "No se pudo cargar el archivo de búsqueda.", lede: "Últimos 30 días. Escribe o filtra para buscar en todo el archivo."
    },
    en: {
      ss: { electricidad: "Electricity", hidrocarburos: "Hydrocarbons", "gas-natural": "Natural gas", petroliferos: "Petroleum products", renovables: "Renewables", mineria: "Mining", general: "Energy (general)" },
      ed: { matutina: "Morning", vespertina: "Evening", extraordinaria: "Extra" },
      rules: "rules", found: function (n, total) { return "<strong>" + n + "</strong> " + (n === 1 ? "result" : "results") + (total > n ? " (showing " + total + ")" : "") + " in the whole archive."; },
      loading: "Loading the archive...", error: "The search archive could not be loaded.", lede: "Last 30 days. Type or filter to search the whole archive."
    }
  };

  var lang = "es";
  var original = new WeakMap();

  function store(key, value) {
    try { if (value === undefined) { return window.localStorage.getItem(key); } window.localStorage.setItem(key, value); } catch (err) { return null; }
    return null;
  }

  function formatDate(iso, fmt) {
    var parts = iso.split("-");
    var d = new Date(Date.UTC(+parts[0], +parts[1] - 1, +parts[2]));
    var locale = lang === "en" ? "en-US" : "es-MX";
    var opts = { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" };
    if (fmt === "short") { opts = { timeZone: "UTC", day: "numeric", month: "short" }; }
    if (fmt === "weekday") { opts.weekday = "long"; }
    var text = new Intl.DateTimeFormat(locale, opts).format(d);
    return lang === "es" ? text.replace(/,/g, "").replace(/\.$/, "") : text;
  }

  function applyLang(next) {
    lang = next === "en" ? "en" : "es";
    document.documentElement.lang = lang === "en" ? "en" : "es-MX";
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (!original.has(el)) { original.set(el, el.textContent); }
      var n = el.getAttribute("data-n");
      if (n !== null && PLURAL[lang][key]) { el.textContent = PLURAL[lang][key](+n); return; }
      if (el.tagName === "OPTION" && el.value === "" && lang === "es") { el.textContent = original.get(el); return; }
      el.textContent = lang === "en" && EN[key] ? EN[key] : original.get(el);
    });
    document.querySelectorAll("[data-en]").forEach(function (el) {
      if (!original.has(el)) { original.set(el, el.textContent); }
      el.textContent = lang === "en" ? el.getAttribute("data-en") : original.get(el);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      if (!el.dataset.es) { el.dataset.es = el.placeholder; }
      var key = el.getAttribute("data-i18n-placeholder");
      el.placeholder = lang === "en" ? EN[key] : el.dataset.es;
    });
    document.querySelectorAll("time[data-fmt]").forEach(function (el) {
      el.textContent = formatDate(el.getAttribute("datetime"), el.getAttribute("data-fmt"));
    });
    var button = document.getElementById("lang");
    if (button) {
      button.textContent = lang === "en" ? "ES" : "EN";
      button.setAttribute("aria-label", lang === "en" ? "Leer en español" : "Read in English");
    }
    document.title = lang === "en" ? "radar·energía · Mexico's energy sector, day by day" : "radar·energía · El día del sector energético en México";
    if (results && !results.hidden) { runSearch(); }
  }

  /* ---------------------------------------------------------------- search */

  var items = null;
  var loading = null;
  var results = document.getElementById("results");
  var archive = document.getElementById("archive");
  var status = document.getElementById("status");
  var form = document.getElementById("search");
  var q = document.getElementById("q");
  var ss = document.getElementById("ss");
  var ag = document.getElementById("ag");
  var src = document.getElementById("src");

  function fold(text) {
    return String(text || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  function esc(text) {
    return String(text).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c]; });
  }
  function terms(query) {
    var out = [];
    String(query).replace(/"([^"]+)"|(\S+)/g, function (_, phrase, word) { out.push(fold(phrase || word)); });
    return out.filter(Boolean);
  }
  function highlight(title, words) {
    if (!words.length) { return esc(title); }
    var folded = fold(title);
    var marks = [];
    words.forEach(function (w) {
      var from = 0, at;
      while (w && (at = folded.indexOf(w, from)) !== -1) { marks.push([at, at + w.length]); from = at + w.length; }
    });
    if (!marks.length) { return esc(title); }
    marks.sort(function (a, b) { return a[0] - b[0]; });
    var html = "", pos = 0;
    marks.forEach(function (m) {
      if (m[0] < pos) { return; }
      html += esc(title.slice(pos, m[0])) + "<mark>" + esc(title.slice(m[0], m[1])) + "</mark>";
      pos = m[1];
    });
    return html + esc(title.slice(pos));
  }
  function card(item, words) {
    var L = LABELS[lang];
    var origin = item.src === "dof"
      ? "<span class=\"src src-dof\">DOF</span><span class=\"meta-ed\">" + esc(L.ed[item.ed] || item.ed) + "</span><span class=\"meta-iss\">" + esc(item.iss || "") + "</span>"
      : "<span class=\"src src-" + esc(item.by.toLowerCase()) + "\">" + esc(item.by) + "</span><span class=\"meta-ed\">" + esc(item.k) + "</span><span class=\"meta-iss\">gob.mx</span>";
    var chips = item.ss.map(function (s) { return "<li class=\"chip ss-" + esc(s) + "\">" + esc(L.ss[s] || s) + "</li>"; })
      .concat(item.ag.map(function (a) { return "<li class=\"chip agency\">" + esc(a) + "</li>"; })).join("");
    return "<li class=\"item\"><p class=\"meta\">" + origin + "<span class=\"meta-date\"><time datetime=\"" + esc(item.d) + "\">" + esc(formatDate(item.d, "long")) + "</time></span></p>" +
      "<h3 class=\"item-title\"><a href=\"" + esc(item.u) + "\" rel=\"noopener\">" + highlight(item.t, words) + "</a></h3>" +
      "<ul class=\"chips\">" + chips + "</ul>" +
      (item.m && item.m.length ? "<p class=\"rules\">" + esc(L.rules) + ": " + esc(item.m.join(", ")) + "</p>" : "") + "</li>";
  }

  function load() {
    if (items) { return Promise.resolve(items); }
    if (!loading) {
      status.textContent = LABELS[lang].loading;
      loading = fetch("data/items.json", { credentials: "omit" })
        .then(function (r) { if (!r.ok) { throw new Error(r.status); } return r.json(); })
        .then(function (data) {
          items = data.map(function (i) {
            var labels = i.ss.map(function (s) { return LABELS.es.ss[s] + " " + LABELS.en.ss[s]; });
            i.f = fold([i.t, i.by, i.k, i.ag.join(" ")].concat(labels).join(" "));
            return i;
          });
          return items;
        });
    }
    return loading;
  }

  function syncUrl() {
    var params = new URLSearchParams(window.location.search);
    [["q", q.value.trim()], ["ss", ss.value], ["ag", ag.value], ["src", src.value]].forEach(function (pair) {
      if (pair[1]) { params.set(pair[0], pair[1]); } else { params.delete(pair[0]); }
    });
    var query = params.toString();
    try { window.history.replaceState(null, "", window.location.pathname + (query ? "?" + query : "") + window.location.hash); } catch (err) { /* file:// */ }
  }

  function runSearch() {
    var active = q.value.trim() || ss.value || ag.value || src.value;
    syncUrl();
    if (!active) {
      results.hidden = true;
      archive.hidden = false;
      status.textContent = LABELS[lang].lede;
      return;
    }
    load().then(function (all) {
      var words = terms(q.value);
      var found = all.filter(function (i) {
        return (!ss.value || i.ss.indexOf(ss.value) !== -1) &&
          (!ag.value || i.ag.indexOf(ag.value) !== -1) &&
          (!src.value || i.src === src.value) &&
          words.every(function (w) { return i.f.indexOf(w) !== -1; });
      });
      var shown = found.slice(0, 300);
      results.innerHTML = "<ul class=\"items\">" + shown.map(function (i) { return card(i, words); }).join("") + "</ul>";
      results.hidden = false;
      archive.hidden = true;
      status.innerHTML = LABELS[lang].found(found.length, shown.length < found.length ? shown.length : 0);
    }).catch(function () {
      status.textContent = LABELS[lang].error;
    });
  }

  var timer = null;
  function onInput() { window.clearTimeout(timer); timer = window.setTimeout(runSearch, 160); }

  if (form) {
    q.addEventListener("input", onInput);
    q.addEventListener("focus", function () { load().catch(function () {}); }, { once: true });
    [ss, ag, src].forEach(function (el) { el.addEventListener("change", runSearch); });
    form.addEventListener("reset", function () { window.setTimeout(runSearch, 0); });
    var params = new URLSearchParams(window.location.search);
    q.value = params.get("q") || "";
    ss.value = params.get("ss") || "";
    ag.value = params.get("ag") || "";
    src.value = params.get("src") || "";
  }

  /* ---------------------------------------------------------------- copy */

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("button.copy");
    if (!button) { return; }
    var text = button.getAttribute("data-copy");
    var done = function () {
      button.textContent = lang === "en" ? EN["feed.copied"] : "Copiado";
      window.setTimeout(function () { button.textContent = lang === "en" ? EN["feed.copy"] : "Copiar"; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { window.prompt("URL", text); });
    } else {
      window.prompt("URL", text);
    }
  });

  /* ---------------------------------------------------------------- boot */

  var wanted = new URLSearchParams(window.location.search).get("lang") || store("radar-lang") || "es";
  var toggle = document.getElementById("lang");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = lang === "en" ? "es" : "en";
      store("radar-lang", next);
      applyLang(next);
    });
  }
  if (wanted === "en") { applyLang("en"); }
  if (form && (q.value || ss.value || ag.value || src.value)) { runSearch(); }
})();
