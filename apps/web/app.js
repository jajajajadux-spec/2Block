const $ = (selector) => document.querySelector(selector);
const status = $("#status");
const dialog = $("#install-dialog");
const defaults = { user: "Guest", avatar: { body: "#58c9a5", head: "#f2c78f", hat: "none" } };
let profile = structuredClone(defaults);
let storageWorks = true;
let config;
let currentAttempt;
const cards = [];

function cleanProfile(value) {
  const user = typeof value?.user === "string" ? value.user.trim().slice(0, 24) : "Guest";
  const color = (v, fallback) => /^#[0-9a-f]{6}$/i.test(v) ? v : fallback;
  return {
    user: user.replace(/[\u0000-\u001f\u007f-\u009f]/g, "") || "Guest",
    avatar: {
      body: color(value?.avatar?.body, defaults.avatar.body),
      head: color(value?.avatar?.head, defaults.avatar.head),
      hat: ["none", "cap", "tall"].includes(value?.avatar?.hat) ? value.avatar.hat : "none",
    },
  };
}

try {
  profile = cleanProfile(JSON.parse(localStorage.getItem("twoblock.guest.v1")));
} catch {
  // A broken old profile or private browsing should never prevent play.
  profile = structuredClone(defaults);
}
$("#username").value = profile.user;
$("#body-color").value = profile.avatar.body;
$("#head-color").value = profile.avatar.head;
$("#hat").value = profile.avatar.hat;

function saveProfile() {
  profile = cleanProfile({ user: $("#username").value, avatar: {
    body: $("#body-color").value, head: $("#head-color").value, hat: $("#hat").value,
  } });
  $("#preview-head").style.backgroundColor = profile.avatar.head;
  $("#preview-body").style.backgroundColor = profile.avatar.body;
  $("#preview-hat").className = profile.avatar.hat;
  try { localStorage.setItem("twoblock.guest.v1", JSON.stringify(profile)); }
  catch { storageWorks = false; status.textContent = "Browser storage is unavailable. Your look will last until this page closes."; }
}
$("#profile").addEventListener("input", saveProfile);
$("#profile").addEventListener("submit", (event) => event.preventDefault());
saveProfile();

async function api(path, body) {
  const response = await fetch(path, { cache: "no-store", signal: AbortSignal.timeout(5000),
    ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The runtime didn't respond.");
  return data;
}

function makeLink(game, ticket) {
  const query = new URLSearchParams({ gameId: game.id, server: config.server,
    user: profile.user, avatar: JSON.stringify(profile.avatar), launchId: ticket.launchId });
  return `twoblock://join?${query}`;
}

async function prepare(card) {
  card.button.disabled = true;
  card.desktop.disabled = true;
  try {
    card.ticket = await api("/api/launches", { gameId: card.game.id });
    card.created = Date.now();
    card.button.disabled = false;
    card.desktop.disabled = false;
  } catch (error) { status.textContent = `${error.message} Reload to reconnect.`; }
}

function stopAttempt() {
  if (!currentAttempt) return;
  clearTimeout(currentAttempt.timer);
  clearTimeout(currentAttempt.poll);
  currentAttempt = undefined;
}

function showFallback(attempt) {
  if (currentAttempt !== attempt || attempt.joined) return;
  if (!dialog.open) dialog.showModal();
}

async function poll(attempt) {
  if (currentAttempt !== attempt) return;
  try {
    const result = await api(`/api/launches/${attempt.ticket.launchId}`);
    if (currentAttempt !== attempt) return;
    if (result.status === "joined") {
      attempt.joined = true;
      status.textContent = "You're in. Have a good time.";
      dialog.close();
      stopAttempt();
      return;
    }
  } catch (error) {
    if (currentAttempt !== attempt) return;
    status.textContent = error.message;
    showFallback(attempt);
    stopAttempt();
    return;
  }
  if (Date.now() - attempt.started < 115000) {
    attempt.poll = setTimeout(() => poll(attempt), 750);
  } else {
    status.textContent = "Launch expired. Click Play Now to try again.";
    stopAttempt();
  }
}

function launch(card, desktop = false) {
  if (!$("#profile").reportValidity()) return;
  if (!card.ticket || Date.now() - card.created > 110000) {
    status.textContent = "Refreshing the launch link. Click Play Now again in a moment.";
    prepare(card);
    return;
  }
  saveProfile();
  if (!desktop) {
    window.location.href = '/play#' + encodeURIComponent(JSON.stringify({
      gameId: card.game.id, user: profile.user, avatar: profile.avatar, launchId: card.ticket.launchId,
    }));
    return;
  }
  stopAttempt();
  dialog.close();
  const attempt = { ticket: card.ticket, started: Date.now(), joined: false };
  currentAttempt = attempt;
  const link = makeLink(card.game, card.ticket);
  $("#retry").href = link;
  status.textContent = `Opening ${card.game.title}… Accept the browser prompt if it appears.`;
  attempt.timer = setTimeout(() => showFallback(attempt), 5000);
  attempt.poll = setTimeout(() => poll(attempt), 500);
  // Tickets are prepared ahead of time so navigation retains the click's user gesture.
  window.location.href = link;
  prepare(card);
}

$("#retry").addEventListener("click", () => {
  status.textContent = "Trying the client again. If the link has expired, use Play Now.";
});

function gameCard(game) {
  const article = document.createElement("article");
  article.className = "game";
  const art = document.createElement("div");
  art.className = `game-art${game.id === "sunset-steps" ? " sunset" : ""}`;
  art.setAttribute("aria-hidden", "true");
  const platform = document.createElement('div');
  platform.className = 'scene-platform';
  art.append(platform);
  for (let i = 0; i < 5; i++) {
    const block = document.createElement('span');
    block.className = `scene-block block-${i}`;
    art.append(block);
  }
  const badge = document.createElement('span');
  badge.className = 'game-badge';
  badge.textContent = '3D · Multiplayer';
  art.append(badge);
  const details = document.createElement("div");
  details.className = "game-details";
  for (const [tag, text, className] of [["span", game.tag, "tag"], ["h3", game.title, ""], ["p", game.description, ""]]) {
    const element = document.createElement(tag);
    element.textContent = text;
    element.className = className;
    details.append(element);
  }
  const button = document.createElement("button");
  button.textContent = "Play Now";
  button.disabled = true;
  button.setAttribute("aria-label", `Play ${game.title}`);
  const desktop = document.createElement('button');
  desktop.textContent = 'Open with desktop launcher';
  desktop.className = 'secondary desktop-launch';
  desktop.disabled = true;
  const card = { game, button, desktop };
  button.addEventListener("click", () => launch(card));
  desktop.addEventListener('click', () => launch(card, true));
  details.append(button, desktop);
  article.append(art, details);
  $("#games").append(article);
  cards.push(card);
  return prepare(card);
}

async function start() {
  try {
    const [settings, catalog] = await Promise.all([api("/api/config"), api("/api/games")]);
    config = settings;
    if (config.windowsInstaller) {
      $("#download").href = config.windowsInstaller;
      $("#download").hidden = false;
    }
    await Promise.all(catalog.games.map(gameCard));
    if (storageWorks && cards.every((card) => !card.button.disabled)) status.textContent = "Ready when you are.";
    setInterval(() => {
      for (const card of cards) if (Date.now() - card.created > 60000) prepare(card);
    }, 15000);
  } catch (error) { status.textContent = `${error.message} Start the runtime, then reload this page.`; }
}
start();
