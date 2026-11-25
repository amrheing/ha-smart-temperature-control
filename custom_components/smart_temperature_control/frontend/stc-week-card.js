// Smart Temperatur Control – week schedule card.
// type: custom:stc-week-card
// entity: climate.schlafzimmer_heizung
const DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

// All colours come from the active Home Assistant theme (CSS variables), so the
// cards follow light/dark mode and themes like Noctis. Each can be overridden in
// a theme or card_mod via the --stc-* variables.
const STC_THEME = `
  :host{
    --stc-surface:var(--ha-card-background,var(--card-background-color,#fff));
    --stc-border:var(--ha-card-border-color,var(--divider-color,#e0e0e0));
    --stc-accent:var(--primary-color,#03a9f4);
    --stc-on-accent:var(--text-primary-color,#fff);
    --stc-comfort-c:var(--stc-comfort,var(--state-climate-heat-color,var(--orange-color,#ff9800)));
    --stc-eco-c:var(--stc-eco,color-mix(in srgb,var(--state-climate-cool-color,var(--blue-color,#2196f3)) 40%,var(--stc-surface)));
  }
  .badge{display:inline-flex;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:600;
    color:color-mix(in srgb,var(--c) 70%,var(--primary-text-color));background:color-mix(in srgb,var(--c) 20%,transparent)}
  .tog{color:var(--primary-text-color);border:1px solid var(--stc-border);background:none}
  .tog.on{background:var(--stc-accent);color:var(--stc-on-accent);border-color:var(--stc-accent)}
`;

class StcWeekCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("climate.")) {
      throw new Error("entity (climate.…) of Smart Temperatur Control required");
    }
    this._config = config;
    this._pending = null;
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config.entity];
    const key = st ? JSON.stringify([st.attributes.days, st.attributes.comfort, st.attributes.eco, st.attributes.schedule_enabled]) : "";
    if (key === this._key && !this._pending) return;
    this._key = key;
    if (this._pending && st && JSON.stringify(st.attributes.days) === JSON.stringify(this._pending)) this._pending = null;
    this._render(st);
  }

  getCardSize() {
    return 6;
  }

  _render(st) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    if (!st) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px">${this._config.entity} nicht gefunden</div></ha-card>`;
      return;
    }
    const days = this._pending || st.attributes.days || [];
    const slots = days.length ? days[0].length : 48;
    const now = new Date();
    const today = (now.getDay() + 6) % 7;
    const nowSlot = Math.floor((now.getHours() * 60 + now.getMinutes()) / (1440 / slots));
    const fmt = (v) => (v == null ? "–" : Number(v).toFixed(1).replace(".", ",") + " °C");
    const title = this._config.title || st.attributes.friendly_name || this._config.entity;
    const dim = st.attributes.schedule_enabled === false ? "opacity:.4;" : "";
    let rows = "";
    days.forEach((row, d) => {
      let cells = "";
      for (let s = 0; s < slots; s++) {
        const k = row[s] === "k";
        const mark = d === today && s === nowSlot ? "box-shadow:inset 0 0 0 2px var(--stc-accent);" : "";
        const hh = String(Math.floor((s * 1440) / slots / 60)).padStart(2, "0");
        const mm = String(((s * 1440) / slots) % 60).padStart(2, "0");
        cells += `<button data-d="${d}" data-s="${s}" title="${DAYS_DE[d]} ${hh}:${mm} ${k ? "Komfort" : "Eco"}" style="background:${k ? "var(--stc-comfort-c)" : "var(--stc-eco-c)"};${mark}"></button>`;
      }
      rows += `<span class="day${d === today ? " today" : ""}">${DAYS_DE[d]}</span><div class="row" style="grid-template-columns:repeat(${slots},minmax(0,1fr));${dim}">${cells}</div>`;
    });
    const wrap = (inner) => (this._config.embedded ? `<div class="emb">${inner}</div>` : `<ha-card>${inner}</ha-card>`);
    this.shadowRoot.innerHTML = `
      <style>${STC_THEME}
        ha-card{padding:16px} .emb{padding:0}
        .head{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px}
        .title{font-weight:600;font-size:16px}
        .legend{display:flex;gap:12px;font-size:12px;color:var(--secondary-text-color)}
        .legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:4px;vertical-align:-2px}
        .grid{display:grid;grid-template-columns:28px minmax(0,1fr);gap:4px 8px;align-items:center}
        .axis{display:flex;justify-content:space-between;font-size:11px;color:var(--secondary-text-color)}
        .day{font-size:12px;color:var(--secondary-text-color)} .day.today{font-weight:700;color:var(--primary-text-color)}
        .row{display:grid;gap:1px;border-radius:6px;overflow:hidden}
        .row button{height:30px;border:none;padding:0;min-width:0;cursor:pointer}
        .foot{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:center;font-size:12px;color:var(--secondary-text-color)}
        .foot button{min-height:36px;padding:0 12px;border-radius:8px;border:1px solid var(--stc-border);background:none;color:var(--primary-text-color);cursor:pointer}
      </style>
      ${wrap(`
        <div class="head"><span class="title">${title}</span>
          <span class="legend"><span><i style="background:var(--stc-comfort-c)"></i>Komfort ${fmt(st.attributes.comfort)}</span><span><i style="background:var(--stc-eco-c)"></i>Eco ${fmt(st.attributes.eco)}</span></span></div>
        <div class="grid"><span></span><div class="axis"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>${rows}</div>
        <div class="foot"><button id="copy">Montag auf Di–Fr kopieren</button><span>Antippen wechselt Komfort ↔ Eco</span></div>
      `)}`;
    this.shadowRoot.querySelectorAll(".row button").forEach((b) =>
      b.addEventListener("click", () => this._toggle(days, +b.dataset.d, +b.dataset.s))
    );
    this.shadowRoot.getElementById("copy").addEventListener("click", () => {
      const next = days.slice();
      for (let d = 1; d < 5; d++) next[d] = days[0];
      this._save(next);
    });
  }

  _toggle(days, d, s) {
    const next = days.slice();
    const row = next[d];
    next[d] = row.slice(0, s) + (row[s] === "k" ? "e" : "k") + row.slice(s + 1);
    this._save(next);
  }

  _save(days) {
    this._pending = days;
    this._render(this._hass.states[this._config.entity]);
    clearTimeout(this._timer);
    // collect several taps, then one service call
    this._timer = setTimeout(() => {
      this._hass.callService("smart_temperature_control", "set_schedule", { days }, { entity_id: this._config.entity });
    }, 800);
  }

  static getStubConfig(hass) {
    const e = Object.keys(hass.states).find((k) => k.startsWith("climate.") && hass.states[k].attributes.days);
    return { entity: e || "climate.heizung_raum" };
  }
}

customElements.define("stc-week-card", StcWeekCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "stc-week-card", name: "Smart Temperatur Control – Wochenplan", description: "Wochenplan eines Raums: Stunde antippen wechselt Komfort/Eco." });

// ---------------------------------------------------------------------------
// Rooms card: one overview box per room; tapping a box opens its details
// directly below it (and closes it again).
// type: custom:stc-rooms-card
// entities: [climate.schlafzimmer_heizung, ...]   (optional, default: all rooms)
const STC_GREY = "var(--grey-color,#9e9e9e)";
const REASONS = {
  comfort: ["Komfort", "var(--stc-comfort-c)"],
  eco: ["Eco", "var(--state-climate-cool-color,var(--blue-color,#2196f3))"],
  manual: ["Manuell", "var(--purple-color,#926bc7)"],
  window: ["Fenster", "var(--teal-color,#009688)"],
  party: ["Party", "var(--pink-color,#e91e63)"],
  vacation: ["Urlaub", STC_GREY],
  summer: ["Sommer", STC_GREY],
  off: ["Aus", STC_GREY],
  permanent_comfort: ["Komfort", "var(--stc-comfort-c)"],
};
const SENSOR_STATUS = {
  ok: "verwendet",
  unavailable: "ignoriert: nicht verfügbar",
  out_of_range: "ignoriert: unplausibel",
  jump: "ignoriert: Sprung",
  stale: "ignoriert: veraltet",
};

class StcRoomsCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._open = null;
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: "full" };
  }

  _rooms() {
    const h = this._hass;
    if (this._config.entities) return this._config.entities;
    return Object.keys(h.states).filter(
      (e) => e.startsWith("climate.") && h.entities?.[e]?.platform === "smart_temperature_control"
    );
  }

  // sibling entity of the same room device, found by its translation key
  _sib(climate, domain, key) {
    const h = this._hass;
    const dev = h.entities?.[climate]?.device_id;
    if (!dev) return null;
    const hit = Object.values(h.entities).find(
      (e) => e.device_id === dev && e.entity_id.startsWith(domain + ".") && e.translation_key === key
    );
    return hit ? hit.entity_id : null;
  }

  set hass(hass) {
    this._hass = hass;
    const ids = this._rooms();
    const watch = [...ids];
    ids.forEach((c) => (hass.states[c]?.attributes.thermostats || []).forEach((t) => watch.push(t)));
    ids.forEach((c) => ["comfort", "eco"].forEach((k) => watch.push(this._sib(c, "number", k))));
    ids.forEach((c) => watch.push(this._sib(c, "switch", "schedule_enabled"), this._sib(c, "switch", "control")));
    const key = JSON.stringify(watch.map((e) => e && hass.states[e] && [hass.states[e].state, hass.states[e].attributes]));
    if (key !== this._key) {
      this._key = key;
      this._render();
    }
    if (this._week) this._week.hass = hass;
  }

  _fmt(v) {
    return v == null || isNaN(v) ? "–" : Number(v).toFixed(1).replace(".", ",") + " °C";
  }

  _time(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const days = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
    const today = new Date().toDateString() === d.toDateString();
    return (today ? "" : days[d.getDay()] + " ") + d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  }

  _reasonText(a) {
    const until = a.until ? " bis " + this._time(a.until) : "";
    switch (a.reason) {
      case "comfort": return "Komfort" + until;
      case "eco": return "Eco" + until;
      case "manual": return "Manuell geändert" + until + ", danach Plan";
      case "window": return "Fenster offen";
      case "party": return "Party" + until;
      case "vacation": return "Urlaub · Thermostate aus";
      case "summer": return "Sommerbetrieb · Thermostate aus";
      case "off": return "Heizung aus · Thermostate ruhen";
      case "permanent_comfort": return "Zeitplan aus · dauerhaft Komfort";
      default: return a.reason || "";
    }
  }

  _name(c, st) {
    const h = this._hass;
    const area = h.entities?.[c]?.area_id || h.devices?.[h.entities?.[c]?.device_id]?.area_id;
    return st.attributes.room || (area && h.areas?.[area]?.name) || st.attributes.friendly_name || c;
  }

  _call(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  _render() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const h = this._hass;
    const ids = this._rooms();
    let boxes = "";
    ids.forEach((c) => {
      const st = h.states[c];
      if (!st) return;
      const a = st.attributes;
      const [label, col] = REASONS[a.reason] || [a.reason, STC_GREY];
      const open = this._open === c;
      const flags = [
        a.control ? "" : '<span class="flag">Lesemodus</span>',
        (a.thermostats || []).length > 1 ? `<span class="flag">${a.thermostats.length} Thermostate</span>` : "",
        a.problem || a.temperature_source !== "sensors" ? '<span class="flag bad">Problem</span>' : "",
      ].join("");
      boxes += `<button class="box${open ? " open" : ""}${a.resting ? " rest" : ""}" data-room="${c}" aria-expanded="${open}">
          <span class="row"><span class="name">${this._name(c, st)}</span></span>
          <span class="row base"><span class="ist">${this._fmt(a.current_temperature)}</span><span class="soll">Soll ${this._fmt(a.temperature)}</span></span>
          <span class="row wrap"><span class="badge" style="--c:${col}">${label}</span>${flags}</span>
          <span class="why">${this._reasonText(a)}</span>
        </button>`;
      if (open) boxes += this._detail(c, st);
    });
    this.shadowRoot.innerHTML = `<style>${StcRoomsCard.css}</style><div class="grid">${boxes || "Keine Räume gefunden"}</div>`;
    this.shadowRoot.querySelectorAll(".box").forEach((b) =>
      b.addEventListener("click", () => {
        this._open = this._open === b.dataset.room ? null : b.dataset.room;
        this._week = null;
        this._render();
      })
    );
    this.shadowRoot.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", () => this._act(b.dataset)));
    const slot = this.shadowRoot.getElementById("week");
    if (slot) {
      if (!this._week) {
        this._week = document.createElement("stc-week-card");
        this._week.setConfig({ entity: this._open, embedded: true, title: "Wochenplan" });
      }
      slot.appendChild(this._week);
      this._week.hass = h;
    }
  }

  _detail(c, st) {
    const h = this._hass;
    const a = st.attributes;
    const sched = this._sib(c, "switch", "schedule_enabled");
    const control = this._sib(c, "switch", "control");
    const on = st.state !== "off";
    const zp = sched && h.states[sched]?.state === "on";
    const ctl = control && h.states[control]?.state === "on";
    const comfort = h.states[this._sib(c, "number", "comfort")]?.state;
    const eco = h.states[this._sib(c, "number", "eco")]?.state;
    const canStep = !a.resting && a.reason !== "window";
    const sensors = Object.entries(a.sensors || {})
      .map(([e, s]) => {
        const n = h.states[e]?.attributes.friendly_name || e;
        return `<div class="kv"><span>${n}</span><span class="${s.status === "ok" ? "" : "bad"}">${this._fmt(s.value)} · ${SENSOR_STATUS[s.status] || s.status}</span></div>`;
      })
      .join("") || `<div class="kv"><span>Kein Raumfühler</span><span class="warn">Thermostat-Fühler</span></div>`;
    const trvs = (a.thermostats || [])
      .map((t) => {
        const ts = h.states[t];
        if (!ts) return `<div class="kv"><span>${t}</span><span class="bad">nicht gefunden</span></div>`;
        const ok = Math.abs(Number(ts.attributes.temperature) - Number(a.temperature)) < 0.25;
        const txt = a.resting ? "ruht" : `Soll ${this._fmt(ts.attributes.temperature)}${ok ? "" : a.control ? " · weicht ab" : " · würde gesetzt"}`;
        return `<div class="kv"><span>${ts.attributes.friendly_name || t}</span><span class="${ok || a.resting ? "" : "warn"}">${txt} · Ist ${this._fmt(ts.attributes.current_temperature)}</span></div>`;
      })
      .join("");
    const manual = a.reason === "manual"
      ? `<div class="manual"><div><strong>Manuell auf ${this._fmt(a.temperature)} gestellt</strong><br><span>gilt bis ${this._time(a.until)}, danach wieder Plan</span></div>
           <div class="btns"><button class="pri" data-act="save" data-e="${c}">Für diese Periode speichern</button><button data-act="plan" data-e="${c}">Zurück zum Plan</button></div></div>`
      : "";
    return `<section class="detail">
      ${manual}
      <div class="col">
        <div class="dhead"><h3>${this._name(c, st)}</h3><button class="x" data-act="close" aria-label="Schließen">×</button></div>
        <div class="dial"><span class="lbl">Soll</span><span class="big">${this._fmt(a.temperature)}</span><span class="lbl">Raum ${this._fmt(a.current_temperature)}</span></div>
        <div class="steps"><button class="round" data-act="step" data-d="-0.5" data-e="${c}" ${canStep ? "" : "disabled"} aria-label="Temperatur senken">−</button>
          <span class="hint">± gilt bis zum nächsten Schaltpunkt</span>
          <button class="round" data-act="step" data-d="0.5" data-e="${c}" ${canStep ? "" : "disabled"} aria-label="Temperatur erhöhen">+</button></div>
        <p class="why c">${this._reasonText(a)}</p>
        <div class="two">
          <button class="tog${on ? " on" : ""}" data-act="heat" data-e="${c}" data-v="${on ? "off" : "heat"}">Heizung ${on ? "an" : "aus"}</button>
          <button class="tog${zp ? " on" : ""}" data-act="sw" data-e="${sched}" data-v="${zp ? "off" : "on"}">Zeitplan ${zp ? "an" : "aus"}</button>
        </div>
        <button class="tog wide${ctl ? " on" : ""}" data-act="sw" data-e="${control}" data-v="${ctl ? "off" : "on"}">Thermostate steuern ${ctl ? "an" : "aus (Lesemodus)"}</button>
      </div>
      <div class="col wide2">
        <div id="week"></div>
        <div class="two">
          <div class="num"><button class="round" data-act="num" data-e="${this._sib(c, "number", "comfort")}" data-v="${Number(comfort) - 0.5}" aria-label="Komfort senken">−</button><span>Komfort<br><strong>${this._fmt(comfort)}</strong></span><button class="round" data-act="num" data-e="${this._sib(c, "number", "comfort")}" data-v="${Number(comfort) + 0.5}" aria-label="Komfort erhöhen">+</button></div>
          <div class="num"><button class="round" data-act="num" data-e="${this._sib(c, "number", "eco")}" data-v="${Number(eco) - 0.5}" aria-label="Eco senken">−</button><span>Eco<br><strong>${this._fmt(eco)}</strong></span><button class="round" data-act="num" data-e="${this._sib(c, "number", "eco")}" data-v="${Number(eco) + 0.5}" aria-label="Eco erhöhen">+</button></div>
        </div>
      </div>
      <div class="col">
        <h4>Raumtemperatur (virtueller Fühler)</h4>${sensors}
        <h4 class="sep">Thermostate</h4>${trvs}
        ${a.problem ? `<p class="bad">${a.problem}</p>` : ""}
      </div>
    </section>`;
  }

  _act(d) {
    const st = d.e && this._hass.states[d.e];
    switch (d.act) {
      case "close":
        this._open = null;
        this._week = null;
        this._render();
        break;
      case "step":
        this._call("climate", "set_temperature", { entity_id: d.e, temperature: Number(st.attributes.temperature) + Number(d.d) });
        break;
      case "heat":
        this._call("climate", "set_hvac_mode", { entity_id: d.e, hvac_mode: d.v });
        break;
      case "plan":
        this._call("climate", "set_preset_mode", { entity_id: d.e, preset_mode: "plan" });
        break;
      case "save": {
        const b = this._sib(d.e, "button", "save_for_period");
        if (b) this._call("button", "press", { entity_id: b });
        break;
      }
      case "sw":
        if (d.e && d.e !== "null") this._call("switch", d.v === "on" ? "turn_on" : "turn_off", { entity_id: d.e });
        break;
      case "num":
        if (d.e && d.e !== "null") this._call("number", "set_value", { entity_id: d.e, value: Number(d.v) });
        break;
    }
  }

  static getStubConfig() {
    return {};
  }
}

StcRoomsCard.css = STC_THEME + `
  :host{display:block}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));grid-auto-flow:row dense;gap:10px}
  button{font-family:inherit;cursor:pointer;color:inherit}
  .box{display:flex;flex-direction:column;gap:8px;text-align:left;padding:14px;border-radius:var(--ha-card-border-radius,14px);min-height:44px;
    background:var(--stc-surface);border:var(--ha-card-border-width,1px) solid var(--stc-border);box-shadow:var(--ha-card-box-shadow,none);
    backdrop-filter:var(--ha-card-backdrop-filter,none);color:var(--primary-text-color)}
  .box.open{border:2px solid var(--stc-accent)}
  .box.rest{opacity:.7}
  .row{display:flex;gap:6px;align-items:center} .row.base{align-items:baseline} .row.wrap{flex-wrap:wrap}
  .name{font-size:14px;font-weight:600}
  .ist{font-size:26px;font-weight:600} .soll{font-size:13px;color:var(--secondary-text-color)}
  .flag{font-size:11px;color:var(--secondary-text-color)} .flag.bad,.bad{color:var(--error-color,#b42318)} .warn{color:var(--warning-color,#b45309)}
  .why{font-size:12px;color:var(--secondary-text-color);line-height:1.35} .why.c{text-align:center;margin:0;font-size:13px}
  .detail{grid-column:1/-1;box-sizing:border-box;background:var(--stc-surface);border:2px solid var(--stc-accent);
    box-shadow:var(--ha-card-box-shadow,none);border-radius:var(--ha-card-border-radius,18px);padding:20px;display:flex;flex-wrap:wrap;gap:24px;color:var(--primary-text-color)}
  .col{flex:1 1 260px;min-width:0;display:flex;flex-direction:column;gap:10px} .col.wide2{flex:999 1 420px}
  .dhead{display:flex;justify-content:space-between;align-items:center} h3{margin:0;font-size:20px} h4{margin:0;font-size:14px} h4.sep{padding-top:12px;border-top:1px solid var(--divider-color)}
  .x{min-width:44px;min-height:44px;border-radius:22px;border:1px solid var(--stc-border);background:none;font-size:18px}
  .dial{display:flex;flex-direction:column;align-items:center;gap:2px;padding:12px 0}
  .big{font-size:44px;font-weight:700} .lbl{font-size:12px;color:var(--secondary-text-color)}
  .steps{display:flex;gap:16px;align-items:center;justify-content:center} .hint{font-size:12px;color:var(--secondary-text-color);max-width:150px;text-align:center}
  .round{width:48px;height:48px;border-radius:24px;border:1px solid var(--stc-border);background:none;font-size:22px;flex:none}
  .round[disabled]{opacity:.35;cursor:default}
  .two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .tog{min-height:44px;border-radius:10px;font-size:14px;font-weight:600}
  .num{display:flex;align-items:center;justify-content:space-between;gap:6px;padding:6px 8px;border-radius:10px;border:1px solid var(--divider-color);font-size:13px;text-align:center}
  .kv{display:flex;justify-content:space-between;gap:8px;font-size:13px} .kv span:last-child{text-align:right}
  .manual{flex:1 1 100%;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px;border-radius:14px;--c:var(--purple-color,#926bc7);
    background:color-mix(in srgb,var(--c) 16%,var(--stc-surface));border:1px solid color-mix(in srgb,var(--c) 45%,transparent);color:var(--primary-text-color);font-size:13px}
  .btns{display:flex;flex-wrap:wrap;gap:8px} .btns button{min-height:44px;padding:0 16px;border-radius:10px;border:1px solid var(--stc-border);background:var(--stc-surface);color:var(--primary-text-color);font-weight:600}
  .btns button.pri{background:var(--stc-accent);color:var(--stc-on-accent);border:none}
`;

customElements.define("stc-rooms-card", StcRoomsCard);
window.customCards.push({ type: "stc-rooms-card", name: "Smart Temperatur Control – Räume", description: "Übersicht aller Räume; Antippen öffnet den Raumregler direkt darunter." });

// ---------------------------------------------------------------------------
// Shared helpers for the table cards
const stcRooms = (h, cfg) =>
  cfg.entities ||
  Object.keys(h.states).filter((e) => e.startsWith("climate.") && h.entities?.[e]?.platform === "smart_temperature_control");
const stcSib = (h, climate, domain, key) => {
  const dev = h.entities?.[climate]?.device_id;
  if (!dev) return null;
  const hit = Object.values(h.entities).find(
    (e) => e.device_id === dev && e.entity_id.startsWith(domain + ".") && e.translation_key === key
  );
  return hit ? hit.entity_id : null;
};
const stcFmt = (v, unit = " °C", digits = 1) =>
  v == null || v === "" || isNaN(v) ? "–" : Number(v).toFixed(digits).replace(".", ",") + unit;
const stcAgo = (iso) => {
  if (!iso) return "–";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "gerade";
  if (min < 60) return `vor ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 48) return `vor ${h} h`;
  return `vor ${Math.floor(h / 24)} Tagen`;
};
const stcDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const stcEsc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const stcMoreInfo = (el, entityId) =>
  el.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));

// ---------------------------------------------------------------------------
// Rooms table: all rooms in one table (like the old Heizen overview).
// type: custom:stc-table-card
class StcTableCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }
  getCardSize() {
    return 6;
  }
  getGridOptions() {
    return { columns: "full" };
  }
  set hass(hass) {
    this._hass = hass;
    const ids = stcRooms(hass, this._config);
    const watch = [];
    ids.forEach((c) => {
      watch.push(c, stcSib(hass, c, "switch", "schedule_enabled"), stcSib(hass, c, "switch", "control"));
    });
    const key = JSON.stringify(watch.map((e) => e && hass.states[e] && [hass.states[e].state, hass.states[e].attributes.temperature,
      hass.states[e].attributes.current_temperature, hass.states[e].attributes.reason, hass.states[e].attributes.comfort, hass.states[e].attributes.eco]));
    if (key !== this._key) {
      this._key = key;
      this._render();
    }
  }
  _render() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => {
        const b = ev.target.closest("[data-act]");
        if (!b) return;
        const d = b.dataset;
        if (d.act === "info") stcMoreInfo(this, d.e);
        else if (d.act === "heat") this._hass.callService("climate", "set_hvac_mode", { entity_id: d.e, hvac_mode: d.v });
        else if (d.act === "sw" && d.e && d.e !== "null")
          this._hass.callService("switch", d.v === "on" ? "turn_on" : "turn_off", { entity_id: d.e });
      });
    }
    const h = this._hass;
    const rows = stcRooms(h, this._config)
      .map((c) => {
        const st = h.states[c];
        if (!st) return "";
        const a = st.attributes;
        const [label, col] = REASONS[a.reason] || [a.reason, STC_GREY];
        const on = st.state !== "off";
        const sched = stcSib(h, c, "switch", "schedule_enabled");
        const control = stcSib(h, c, "switch", "control");
        const zp = sched ? h.states[sched]?.state === "on" : a.schedule_enabled;
        const ctl = control ? h.states[control]?.state === "on" : a.control;
        const bad = a.problem || a.temperature_source !== "sensors" || (a.devices || []).some((d) => d.issues.length);
        const name = stcEsc(a.room || a.friendly_name || c);
        return `<tr>
          <th scope="row"><button class="link" data-act="info" data-e="${c}">${name}</button>${bad ? ' <span class="dot" title="Hinweis"></span>' : ""}</th>
          <td class="n">${stcFmt(a.current_temperature)}</td>
          <td class="n"><strong>${stcFmt(a.temperature)}</strong></td>
          <td><span class="badge" style="--c:${col}">${label}</span></td>
          <td><button class="tog${on ? " on" : ""}" data-act="heat" data-e="${c}" data-v="${on ? "off" : "heat"}" aria-pressed="${on}">${on ? "an" : "aus"}</button></td>
          <td><button class="tog${zp ? " on" : ""}${on ? "" : " dim"}" data-act="sw" data-e="${sched}" data-v="${zp ? "off" : "on"}" aria-pressed="${zp}">${zp ? "an" : "aus"}</button></td>
          <td><button class="tog${ctl ? " on" : ""}" data-act="sw" data-e="${control}" data-v="${ctl ? "off" : "on"}" aria-pressed="${ctl}">${ctl ? "an" : "Lesen"}</button></td>
          <td class="n">${stcFmt(a.comfort)}</td>
          <td class="n">${stcFmt(a.eco)}</td>
        </tr>`;
      })
      .join("");
    this.shadowRoot.innerHTML = `<style>${StcTableCard.css}</style><ha-card><div class="wrap"><table>
      <thead><tr><th scope="col">Raum</th><th scope="col" class="n">Ist</th><th scope="col" class="n">Soll</th><th scope="col">Grund</th>
      <th scope="col">Heizung</th><th scope="col">Zeitplan</th><th scope="col">Steuern</th><th scope="col" class="n">Komfort</th><th scope="col" class="n">Eco</th></tr></thead>
      <tbody>${rows}</tbody></table></div></ha-card>`;
  }
  static getStubConfig() {
    return {};
  }
}
StcTableCard.css = STC_THEME + `
  ha-card{padding:8px 4px}
  .wrap{overflow-x:auto}
  table{width:100%;border-collapse:collapse;font-size:14px;color:var(--primary-text-color)}
  th,td{padding:6px 8px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--divider-color,#e5e2dc)}
  thead th{font-size:12px;font-weight:600;color:var(--secondary-text-color)}
  tbody tr:last-child th,tbody tr:last-child td{border-bottom:none}
  th[scope=row],thead th:first-child{position:sticky;left:0;z-index:1;background:var(--stc-surface)}
  .n{text-align:right;font-variant-numeric:tabular-nums}
  button{font-family:inherit;cursor:pointer;color:inherit}
  .link{background:none;border:none;padding:8px 0;font-size:14px;font-weight:600;text-align:left}
  .tog{min-width:56px;min-height:36px;border-radius:8px;font-size:13px;font-weight:600}
  .tog.dim{opacity:.35}
  .dot{display:inline-block;width:8px;height:8px;border-radius:4px;background:var(--error-color,#b42318);vertical-align:middle}
`;
customElements.define("stc-table-card", StcTableCard);
window.customCards.push({ type: "stc-table-card", name: "Smart Temperatur Control – Raumtabelle", description: "Alle Räume als Tabelle: Ist, Soll, Grund, Heizung, Zeitplan, Steuern, Komfort/Eco." });

// ---------------------------------------------------------------------------
// Devices: every physical thermostat with reachability, battery, radio, function.
// type: custom:stc-devices-card
const ISSUES = {
  unavailable: "nicht erreichbar",
  battery_low: "Batterie schwach",
  stale: "meldet sich nicht",
  weak_signal: "Funk schwach",
  mounting_mode: "Montagemodus",
  firmware_update: "Firmware-Update",
};
class StcDevicesCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }
  getCardSize() {
    return 8;
  }
  getGridOptions() {
    return { columns: "full" };
  }
  set hass(hass) {
    this._hass = hass;
    const ids = stcRooms(hass, this._config);
    this._fetchHistory(ids);
    const key = JSON.stringify(ids.map((c) => {
      const a = hass.states[c]?.attributes || {};
      return [a.temperature, a.resting, a.control, (a.devices || []).map((d) => ({ ...d, last_seen: stcAgo(d.last_seen) }))];
    })) + (this._histAt || "");
    if (key !== this._key) {
      this._key = key;
      this._render();
    }
  }
  // Offline periods of every TRV from the recorder (also from before the integration existed).
  async _fetchHistory(ids) {
    const h = this._hass;
    const trvs = [];
    ids.forEach((c) => (h.states[c]?.attributes.devices || []).forEach((d) => trvs.push(d.entity_id)));
    const want = trvs.sort().join(",");
    if (!want || this._histLoading || (this._histKey === want && Date.now() - (this._histAt || 0) < 15 * 60000)) return;
    this._histLoading = true;
    const days = this._config.days || 14;
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    start.setDate(start.getDate() - (days - 1));
    try {
      const res = await h.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        entity_ids: trvs,
        minimal_response: true,
        no_attributes: true,
        significant_changes_only: false,
      });
      const out = {};
      const now = Date.now();
      for (const id of trvs) {
        const rows = res[id] || [];
        const perDay = {};
        const add = (t0, t1, offline, count) => {
          // split [t0, t1) over local days
          let t = t0;
          while (t < t1) {
            const d = new Date(t);
            const key = stcDay(d);
            d.setHours(24, 0, 0, 0);
            const end = Math.min(t1, d.getTime());
            const slot = (perDay[key] = perDay[key] || { offline: 0, offline_min: 0 });
            if (offline) slot.offline_min += (end - t) / 60000;
            if (count && t === t0) slot.offline += 1;
            t = end;
          }
        };
        rows.forEach((r, i) => {
          const t0 = Math.max(start.getTime(), (r.lu ?? Date.parse(r.last_updated) / 1000) * 1000);
          const t1 = i + 1 < rows.length ? (rows[i + 1].lu ?? Date.parse(rows[i + 1].last_updated) / 1000) * 1000 : now;
          const st = r.s ?? r.state;
          const off = st === "unavailable";
          const prev = i > 0 ? rows[i - 1].s ?? rows[i - 1].state : null;
          add(t0, t1, off, off && i > 0 && prev !== "unavailable");
        });
        out[id] = perDay;
      }
      this._hist = out;
      this._histKey = want;
      this._histAt = Date.now();
    } catch (e) {
      this._histAt = Date.now(); // no recorder access: show the integration's own counters only
    }
    this._histLoading = false;
    this._key = null;
    this.hass = this._hass;
  }

  _chart(d) {
    const days = this._config.days || 14;
    const stats = d.stats || {};
    const hist = this._hist?.[d.entity_id] || {};
    const cols = [];
    for (let i = days - 1; i >= 0; i--) {
      const dt = new Date();
      dt.setHours(12, 0, 0, 0);
      dt.setDate(dt.getDate() - i);
      const key = stcDay(dt);
      const s = stats[key] || {};
      const hh = hist[key] || {};
      cols.push({
        date: dt,
        offline: Math.max(s.offline || 0, hh.offline || 0),
        offline_min: Math.round(Math.max(s.offline_min || 0, hh.offline_min || 0)),
        cmd: (s.retry || 0) + (s.send_error || 0),
        failed: s.not_applied || 0,
      });
    }
    const max = Math.max(3, ...cols.map((c) => c.offline + c.cmd + c.failed));
    const W = 18, GAP = 4, H = 40;
    let bars = "";
    cols.forEach((c, i) => {
      const x = i * (W + GAP);
      let y = H;
      const seg = (n, color, label) => {
        if (!n) return;
        const hgt = Math.max(3, (n / max) * H);
        y -= hgt;
        bars += `<rect x="${x}" y="${y}" width="${W}" height="${hgt - 1}" rx="2" fill="${color}"><title>${label}</title></rect>`;
      };
      const dl = c.date.toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });
      seg(c.offline, "var(--error-color,#b42318)", `${dl}: ${c.offline}× offline`);
      seg(c.cmd, "var(--warning-color,#b45309)", `${dl}: ${c.cmd}× Befehl wiederholt/fehlgeschlagen`);
      seg(c.failed, "var(--deep-orange-color,#ff6f22)", `${dl}: ${c.failed}× Sollwert nicht übernommen`);
      if (!c.offline && !c.cmd && !c.failed) bars += `<rect x="${x}" y="${H - 2}" width="${W}" height="2" rx="1" fill="var(--divider-color,#dad7d1)"/>`;
      const avail = c.offline_min === 0 ? "var(--success-color,#15803d)" : c.offline_min < 60 ? "var(--warning-color,#b45309)" : "var(--error-color,#b42318)";
      bars += `<rect x="${x}" y="${H + 4}" width="${W}" height="4" rx="2" fill="${avail}" opacity="${c.offline_min ? 1 : 0.35}"><title>${dl}: ${c.offline_min ? c.offline_min + " min nicht erreichbar" : "immer erreichbar"}</title></rect>`;
    });
    const sum = cols.reduce((a, c) => ({ offline: a.offline + c.offline, min: a.min + c.offline_min, cmd: a.cmd + c.cmd, failed: a.failed + c.failed }), { offline: 0, min: 0, cmd: 0, failed: 0 });
    const dur = sum.min >= 60 ? `${Math.floor(sum.min / 60)} h ${sum.min % 60} min` : `${sum.min} min`;
    const text = sum.offline || sum.cmd || sum.failed || sum.min
      ? `${days} Tage: ` + [
          sum.offline || sum.min ? `${sum.offline}× offline (${dur})` : "",
          sum.cmd ? `${sum.cmd}× Befehl wiederholt` : "",
          sum.failed ? `${sum.failed}× nicht übernommen` : "",
        ].filter(Boolean).join(" · ")
      : `${days} Tage ohne Fehler`;
    const width = days * (W + GAP) - GAP;
    const first = cols[0].date.toLocaleDateString("de-DE", { day: "numeric", month: "numeric" });
    return `<div class="chartbox"><svg viewBox="0 0 ${width} ${H + 8}" width="${width}" height="${H + 8}" role="img" aria-label="${text}">${bars}</svg>
      <div class="ctext"><span class="${sum.offline || sum.failed ? "bad" : sum.cmd ? "warn" : "muted"}">${text}</span><span class="muted">${first} bis heute · rot offline, orange Befehl wiederholt, Streifen = Erreichbarkeit</span></div></div>`;
  }

  _val(x, unit, digits = 0) {
    if (!x) return "–";
    if (x.disabled) return '<span class="muted" title="Entität ist in Home Assistant deaktiviert">deaktiviert</span>';
    return stcFmt(x.value, unit, digits);
  }
  _onoff(x, good) {
    if (!x || x.disabled || x.value == null) return "–";
    const on = x.value === "on";
    const cls = good === undefined ? "" : on === good ? "" : "warn";
    return `<span class="${cls}">${on ? "an" : "aus"}</span>`;
  }
  _render() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => {
        const b = ev.target.closest("[data-act=info]");
        if (b) stcMoreInfo(this, b.dataset.e);
      });
    }
    const h = this._hass;
    let total = 0;
    let withIssues = 0;
    const rows = stcRooms(h, this._config)
      .map((c) => {
        const st = h.states[c];
        if (!st) return "";
        const a = st.attributes;
        const room = stcEsc(a.room || a.friendly_name || c);
        return (a.devices || [])
          .map((d) => {
            total += 1;
            const issues = [...d.issues];
            const okSet = a.resting ? true : d.setpoint != null && Math.abs(Number(d.setpoint) - Number(a.temperature)) < 0.3;
            if (!okSet && a.control) issues.push("setpoint");
            if (issues.length) withIssues += 1;
            const state = !d.available ? ["bad", "offline"] : issues.length ? ["warn", "Hinweis"] : ["ok", "OK"];
            const chips = issues
              .map((i) => `<span class="chip ${i === "unavailable" || i === "battery_low" ? "bad" : "warn"}">${i === "setpoint" ? "Soll weicht ab" : ISSUES[i] || i}</span>`)
              .join("");
            const radio = d.rssi && !d.rssi.disabled ? `${this._val(d.rssi, " dBm")}` : "";
            const lqi = d.lqi && !d.lqi.disabled ? `LQI ${this._val(d.lqi, "")}` : "";
            const radioTxt = radio || lqi ? [radio, lqi].filter(Boolean).join(" · ") : this._val(d.rssi || d.lqi, "");
            return `<tr>
              <th scope="row"><button class="link" data-act="info" data-e="${d.entity_id}">${stcEsc(d.name)}</button><div class="sub">${room}${d.model ? " · " + stcEsc(d.model) : ""}</div></th>
              <td><span class="st ${state[0]}">${state[1]}</span></td>
              <td>${stcAgo(d.last_seen)}</td>
              <td class="n">${this._val(d.battery, " %")}</td>
              <td class="n">${radioTxt}</td>
              <td class="n">${stcFmt(d.setpoint)}<div class="sub">${a.resting ? "ruht" : okSet ? "= Raum" : "Raum " + stcFmt(a.temperature)}</div></td>
              <td class="n">${stcFmt(d.local_temperature)}</td>
              <td class="n">${this._val(d.heat_demand, " %")}</td>
              <td>${this._onoff(d.window_detection, false)}</td>
              <td>${this._onoff(d.external_priority, true)}</td>
              <td class="chips">${chips}</td>
            </tr>
            <tr class="chartrow"><td colspan="11">${this._chart(d)}</td></tr>`;
          })
          .join("");
      })
      .join("");
    this.shadowRoot.innerHTML = `<style>${StcDevicesCard.css}</style><ha-card>
      <div class="head"><strong>${total} Thermostate</strong><span class="${withIssues ? "warn" : "muted"}">${withIssues ? withIssues + " mit Hinweis" : "alle OK"}</span></div>
      <div class="wrap"><table>
      <thead><tr><th scope="col">Thermostat</th><th scope="col">Status</th><th scope="col">Zuletzt</th><th scope="col" class="n">Batterie</th>
      <th scope="col" class="n">Funk</th><th scope="col" class="n">Soll TRV</th><th scope="col" class="n">Ist TRV</th><th scope="col" class="n">Ventil</th>
      <th scope="col">Eigene Fenstererk.</th><th scope="col">Ext. Fühler</th><th scope="col">Hinweise</th></tr></thead>
      <tbody>${rows}</tbody></table></div></ha-card>`;
  }
  static getStubConfig() {
    return {};
  }
}
StcDevicesCard.css = STC_THEME + `
  ha-card{padding:8px 4px}
  .head{display:flex;gap:12px;align-items:baseline;padding:4px 8px 8px;font-size:14px;color:var(--primary-text-color)}
  .wrap{overflow-x:auto}
  table{width:100%;border-collapse:collapse;font-size:13px;color:var(--primary-text-color)}
  th,td{padding:6px 8px;text-align:left;white-space:nowrap;vertical-align:top;border-bottom:1px solid var(--divider-color,#e5e2dc)}
  thead th{font-size:12px;font-weight:600;color:var(--secondary-text-color);vertical-align:bottom}
  tbody tr:last-child th,tbody tr:last-child td{border-bottom:none}
  th[scope=row],thead th:first-child{position:sticky;left:0;z-index:1;background:var(--stc-surface)}
  .n{text-align:right;font-variant-numeric:tabular-nums}
  .sub{font-size:11px;font-weight:400;color:var(--secondary-text-color)}
  .link{background:none;border:none;padding:0;font:inherit;font-weight:600;cursor:pointer;color:inherit;text-align:left}
  .st{display:inline-flex;align-items:center;gap:6px;font-weight:600}
  .st::before{content:"";width:8px;height:8px;border-radius:4px;background:currentColor}
  .st.ok{color:var(--success-color,#15803d)} .st.warn,.warn{color:var(--warning-color,#b45309)} .st.bad,.bad{color:var(--error-color,#b42318)}
  .muted{color:var(--secondary-text-color)}
  .chips{white-space:normal;min-width:120px}
  tr:has(+ .chartrow) th,tr:has(+ .chartrow) td{border-bottom:none}
  .chartrow td{padding:0 8px 10px}
  .chartbox{position:sticky;left:8px;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;max-width:calc(100vw - 72px)}
  .chartbox svg{flex:none;overflow:visible}
  .ctext{display:flex;flex-direction:column;gap:2px;font-size:12px;white-space:normal;min-width:180px;flex:1}
  .chip{display:inline-block;margin:0 4px 4px 0;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;border:1px solid currentColor}
`;
customElements.define("stc-devices-card", StcDevicesCard);
window.customCards.push({ type: "stc-devices-card", name: "Smart Temperatur Control – Thermostate", description: "Alle physischen Thermostate: Erreichbarkeit, Batterie, Funk, Sollwert, Ventil." });
