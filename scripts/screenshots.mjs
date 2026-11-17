/**
 * Serves docs/ locally, captures the README screenshots and the Open Graph image with
 * the locally installed Google Chrome (playwright-core, no browser download), and runs
 * smoke checks: no console errors, no horizontal scroll on a phone, search and the
 * English toggle work.
 *
 *   uv run radar-energia build
 *   PLAYWRIGHT_CORE=/path/to/node_modules/playwright-core node scripts/screenshots.mjs
 *
 * PLAYWRIGHT_CORE defaults to "playwright-core" (resolved from node_modules).
 * CHROME_PATH selects another Chromium binary.
 */
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { extname, join, normalize, resolve } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_CORE || "playwright-core");

const ROOT = resolve(import.meta.dirname, "..");
const DOCS = join(ROOT, "docs");
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
  ".xml": "application/atom+xml; charset=utf-8",
  ".png": "image/png",
  ".woff2": "font/woff2",
};

function serve() {
  const server = createServer((req, res) => {
    const path = decodeURIComponent(new URL(req.url ?? "/", "http://x").pathname);
    const file = normalize(join(DOCS, path.endsWith("/") ? `${path}index.html` : path));
    if (!file.startsWith(DOCS)) return void res.writeHead(403).end();
    readFile(file).then(
      (body) => res.writeHead(200, { "content-type": TYPES[extname(file)] ?? "application/octet-stream" }).end(body),
      () => res.writeHead(404).end("not found"),
    );
  });
  return new Promise((ok) => {
    server.listen(0, "127.0.0.1", () => ok({ server, url: `http://127.0.0.1:${server.address().port}/` }));
  });
}

function check(condition, message) {
  if (!condition) throw new Error(`Check failed: ${message}`);
  console.log(`ok  ${message}`);
}

const { server, url } = await serve();
const browser = await chromium.launch(
  process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: "chrome" },
);
const errors = [];
try {
  const desktop = await browser.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 2 });
  desktop.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  desktop.on("pageerror", (e) => errors.push(String(e)));
  await desktop.emulateMedia({ reducedMotion: "reduce" });
  await desktop.goto(url, { waitUntil: "networkidle" });
  await desktop.evaluate(() => document.fonts.ready);
  await desktop.screenshot({ path: join(ROOT, "assets/screenshot-desktop.png") });
  console.log("wrote assets/screenshot-desktop.png");

  await desktop.locator("#mercados").scrollIntoViewIfNeeded();
  await desktop.evaluate(() => window.scrollTo(0, document.querySelector("#mercados").offsetTop - 60));
  await desktop.screenshot({ path: join(ROOT, "assets/screenshot-markets.png") });
  console.log("wrote assets/screenshot-markets.png");

  await desktop.fill("#q", "gas natural");
  await desktop.waitForSelector("#results .item");
  const found = await desktop.locator("#results .item").count();
  check(found > 0, `search "gas natural" returns ${found} items`);
  await desktop.evaluate(() => window.scrollTo(0, document.querySelector("#archivo").offsetTop - 60));
  await desktop.screenshot({ path: join(ROOT, "assets/screenshot-search.png") });
  console.log("wrote assets/screenshot-search.png");

  await desktop.click("#clear");
  await desktop.waitForSelector("#archive:not([hidden])");
  await desktop.click("#lang");
  const title = await desktop.textContent("#dof-title");
  check(/Official Gazette/.test(title), "English toggle translates headings");
  check((await desktop.getAttribute("html", "lang")) === "en", "html lang switches to en");
  await desktop.click("#lang");

  const og = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  await og.emulateMedia({ reducedMotion: "reduce" });
  await og.goto(url, { waitUntil: "networkidle" });
  await og.evaluate(() => document.fonts.ready);
  await og.screenshot({ path: join(DOCS, "assets/og.png") });
  console.log("wrote docs/assets/og.png");

  const phone = await browser.newPage({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  phone.on("pageerror", (e) => errors.push(String(e)));
  await phone.emulateMedia({ reducedMotion: "reduce" });
  await phone.goto(url, { waitUntil: "networkidle" });
  await phone.evaluate(() => document.fonts.ready);
  const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(overflow <= 0, `no horizontal scroll at 375 px (overflow ${overflow}px)`);
  await phone.screenshot({ path: join(ROOT, "assets/screenshot-mobile.png") });
  console.log("wrote assets/screenshot-mobile.png");

  const unlabelled = await phone.evaluate(
    () => [...document.querySelectorAll("input, select, button")].filter((el) => !(el.labels?.length || el.getAttribute("aria-label") || el.textContent.trim())).length,
  );
  check(unlabelled === 0, "every control has a label");
  check(errors.length === 0, `no console errors${errors.length ? `: ${errors.join(" | ")}` : ""}`);
} finally {
  await browser.close();
  server.close();
}
