// Smart Temperatur Control – week schedule card.
// type: custom:stc-week-card
// entity: climate.schlafzimmer_heizung
const DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

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
        const mark = d === today && s === nowSlot ? "box-shadow:inset 0 0 0 2px var(--primary-text-color);" : "";
        const hh = String(Math.floor((s * 1440) / slots / 60)).padStart(2, "0");
        const mm = String(((s * 1440) / slots) % 60).padStart(2, "0");
        cells += `<button data-d="${d}" data-s="${s}" title="${DAYS_DE[d]} ${hh}:${mm} ${k ? "Komfort" : "Eco"}" style="background:${k ? "var(--stc-comfort,#f97316)" : "var(--stc-eco,#bfd0fb)"};${mark}"></button>`;
      }
      rows += `<span class="day${d === today ? " today" : ""}">${DAYS_DE[d]}</span><div class="row" style="grid-template-columns:repeat(${slots},minmax(0,1fr));${dim}">${cells}</div>`;
    });
    this.shadowRoot.innerHTML = `
      <style>
        ha-card{padding:16px}
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
        .foot button{min-height:36px;padding:0 12px;border-radius:8px;border:1px solid var(--divider-color);background:none;color:var(--primary-text-color);cursor:pointer}
      </style>
      <ha-card>
        <div class="head"><span class="title">${title}</span>
          <span class="legend"><span><i style="background:var(--stc-comfort,#f97316)"></i>Komfort ${fmt(st.attributes.comfort)}</span><span><i style="background:var(--stc-eco,#bfd0fb)"></i>Eco ${fmt(st.attributes.eco)}</span></span></div>
        <div class="grid"><span></span><div class="axis"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>${rows}</div>
        <div class="foot"><button id="copy">Montag auf Di–Fr kopieren</button><span>Antippen wechselt Komfort ↔ Eco</span></div>
      </ha-card>`;
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
