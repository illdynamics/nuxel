/* Nuxel Doom — original touch-first raycasting engine.
 *
 * This is an original Nuxel game: no copyrighted DOOM assets, no WAD files and
 * no external engine required.  It renders a textured 3D maze into a small
 * internal framebuffer, scales it with nearest-neighbour sampling, and exposes
 * a deterministic update loop that the touch HUD and the tests both drive.
 */
(function (global) {
  'use strict';

  const MAP_LEGEND = {
    '.': 0, '#': 1, b: 2, m: 3, D: 4, P: 0, X: 0,
    i: 0, z: 0, c: 0, h: 0, a: 0, s: 0, r: 0,
  };
  const WALL_COLORS = {
    1: { light: '#8a4b3c', dark: '#4a211c', edge: '#c77a58' },
    2: { light: '#6d5a45', dark: '#33281f', edge: '#a68a63' },
    3: { light: '#58606a', dark: '#252b33', edge: '#9aa7b5' },
    4: { light: '#9b6a21', dark: '#4b2d08', edge: '#ffb347' },
  };
  const WEAPONS = [
    { id: 'pistol', name: 'PISTOL', ammo: 'bullets', damage: 20, pellets: 1, spread: 0, cooldown: 0.34, sound: 'pistol' },
    { id: 'shotgun', name: 'SHOTGUN', ammo: 'shells', damage: 13, pellets: 6, spread: 0.19, cooldown: 0.82, sound: 'shotgun' },
    { id: 'plasma', name: 'PLASMA', ammo: 'cells', damage: 16, pellets: 1, spread: 0.035, cooldown: 0.15, sound: 'plasma' },
  ];
  const DEMON_ART = [
    '................',
    '.....hh..hh.....',
    '....hddhhddh....',
    '...hddddddddh...',
    '...hdRddddRdh...',
    '...hdddTTdddh...',
    '...hdddddddhh...',
    '....hddddddh....',
    '..hh.ddddd..hh..',
    '.hddhddddddhddh.',
    '.hddddddddddddh.',
    '..hhhddddddhhh..',
    '....hdd..ddh....',
    '....hdd..ddh....',
    '...hhh....hhh...',
    '................',
  ];
  const ZOMBIE_ART = [
    '................',
    '.....gg..gg.....',
    '....gggggggg....',
    '...ggWggggWgg...',
    '...gggggggggg...',
    '...ggggRRgggg...',
    '....gggggggg....',
    '.....gggggg.....',
    '...gggggggggg...',
    '..gg.gggggg.gg..',
    '..gggggggggggg..',
    '...gggggggggg...',
    '....ggg..ggg....',
    '....ggg..ggg....',
    '....gg....gg....',
    '................',
  ];
  const HELL_ART = [
    '................',
    '....rr....rr....',
    '...rrrrrrrrrr...',
    '..rrRRrrrrRRrr..',
    '..rrrrYYYYrrrr..',
    '..rrrrrrrrrrrr..',
    '...rrrrrrrrrr...',
    '....rrrrrrrr....',
    '..rrrrrrrrrrrr..',
    '.rrrr.rrrr.rrrr.',
    '.rrr..rrrr..rrr.',
    '..rr..rrrr..rr..',
    '......rrrr......',
    '.....rr..rr.....',
    '....rrr..rrr....',
    '................',
  ];
  const PIXEL_COLORS = {
    h: '#7a2b24', d: '#b8412f', R: '#ffd166', T: '#f4f1de', g: '#4f7f45',
    W: '#d9ed92', Y: '#ffcc00', r: '#6b1b2b',
  };

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }

  class DoomEngine {
    constructor(options) {
      options = options || {};
      this.width = options.width || 320;
      this.height = options.height || 180;
      this.levels = options.levels || DoomEngine.LEVELS;
      this.spriteScale = 2;
      this.sprites = {};
      this._buildSprites();
      this.reset(0);
    }

    reset(levelIndex) {
      this.levelIndex = clamp(levelIndex || 0, 0, this.levels.length - 1);
      const level = this.levels[this.levelIndex];
      this.map = level.map.map(row => row.split(''));
      this.mapW = this.map[0].length;
      this.mapH = this.map.length;
      this.doors = {};
      this.enemies = [];
      this.pickups = [];
      this.exit = { x: 1.5, y: 1.5 };
      this.start = { x: 1.5, y: 1.5 };
      for (let y = 0; y < this.mapH; y++) {
        for (let x = 0; x < this.mapW; x++) {
          const c = this.map[y][x];
          if (c === 'P') { this.start = { x: x + 0.5, y: y + 0.5 }; this.map[y][x] = '.'; }
          else if (c === 'X') { this.exit = { x: x + 0.5, y: y + 0.5 }; this.map[y][x] = '.'; }
          else if (c === 'D') { this.doors[x + ',' + y] = { open: 0, opening: false }; }
          else if (c === 'i' || c === 'z' || c === 'c') {
            this.enemies.push({
              x: x + 0.5, y: y + 0.5, kind: c, hp: c === 'c' ? 90 : c === 'z' ? 45 : 60,
              alive: true, hurt: 0, cooldown: 0.5 + Math.random() * 0.7, speed: c === 'c' ? 1.0 : 0.68,
            });
            this.map[y][x] = '.';
          } else if (c === 'h' || c === 'a' || c === 's' || c === 'r') {
            this.pickups.push({ x: x + 0.5, y: y + 0.5, kind: c, taken: false });
            this.map[y][x] = '.';
          } else if (c === ' ') {
            this.map[y][x] = '#';
          }
        }
      }
      this.player = {
        x: this.start.x, y: this.start.y, yaw: -Math.PI / 2, pitch: 0,
        health: 100, armor: 0, bullets: 48, shells: 12, cells: 24,
        weapon: 0, run: false, fireCooldown: 0, hurtTimer: 0,
      };
      this.muzzle = 0;
      this.damageFlash = 0;
      this.crosshairPulse = 0;
      this.particles = [];
      this.state = 'playing';
      this.kills = 0;
      this.totalEnemies = this.enemies.length;
      this.message = level.name || 'SECTOR ' + (this.levelIndex + 1);
      this.messageTimer = 2.5;
      return this;
    }

    _buildSprites() {
      this.sprites = {};
      if (typeof document === 'undefined') return;
      const make = (art) => {
        const size = art.length;
        const c = document.createElement('canvas');
        c.width = size; c.height = size;
        const g = c.getContext('2d');
        for (let y = 0; y < size; y++) {
          for (let x = 0; x < size; x++) {
            const ch = art[y][x];
            const color = PIXEL_COLORS[ch];
            if (!color) continue;
            g.fillStyle = color;
            g.fillRect(x, y, 1, 1);
          }
        }
        return c;
      };
      const normal = { i: make(DEMON_ART), z: make(ZOMBIE_ART), c: make(HELL_ART) };
      this.sprites.enemy = normal;
      this.sprites.enemyHurt = {};
      for (const k of Object.keys(normal)) {
        const c = document.createElement('canvas');
        c.width = normal[k].width; c.height = normal[k].height;
        const g = c.getContext('2d');
        g.drawImage(normal[k], 0, 0);
        g.globalCompositeOperation = 'source-atop';
        g.fillStyle = 'rgba(255,70,40,.72)';
        g.fillRect(0, 0, c.width, c.height);
        this.sprites.enemyHurt[k] = c;
      }
    }

    tileAt(x, y) {
      const tx = Math.floor(x), ty = Math.floor(y);
      if (tx < 0 || ty < 0 || tx >= this.mapW || ty >= this.mapH) return 1;
      const c = this.map[ty][tx];
      const door = this.doors[tx + ',' + ty];
      if (c === 'D') return door && door.open > 0.72 ? 0 : 4;
      return MAP_LEGEND[c] || 0;
    }

    blocked(x, y) {
      return this.tileAt(x, y) !== 0;
    }

    _lineOfSight(x1, y1, x2, y2) {
      const dx = x2 - x1, dy = y2 - y1;
      const steps = Math.ceil(Math.hypot(dx, dy) * 8);
      for (let i = 1; i < steps; i++) {
        const t = i / steps;
        if (this.blocked(x1 + dx * t, y1 + dy * t)) return false;
      }
      return true;
    }

    use() {
      const reach = 1.25;
      const dirX = Math.cos(this.player.yaw), dirY = Math.sin(this.player.yaw);
      for (let d = 0.2; d <= reach; d += 0.2) {
        const x = Math.floor(this.player.x + dirX * d);
        const y = Math.floor(this.player.y + dirY * d);
        const door = this.doors[x + ',' + y];
        if (door && !door.opening && door.open < 1) {
          door.opening = true;
          this._say('DOOR UNLOCKED');
          return 'door';
        }
      }
      if (Math.hypot(this.player.x - this.exit.x, this.player.y - this.exit.y) < 0.9) {
        this.nextLevel();
        return 'exit';
      }
      this._say('NOTHING TO USE');
      return null;
    }

    switchWeapon(delta) {
      const order = [0, 1, 2];
      let idx = order.indexOf(this.player.weapon);
      for (let i = 0; i < 3; i++) {
        idx = (idx + delta + 3) % 3;
        const w = WEAPONS[idx];
        if (this.player[w.ammo] > 0 || idx === 0) { this.player.weapon = idx; this._say(w.name); return idx; }
      }
      return this.player.weapon;
    }

    selectWeapon(index) {
      if (index < 0 || index >= WEAPONS.length) return this.player.weapon;
      const w = WEAPONS[index];
      if (index !== 0 && this.player[w.ammo] <= 0) { this._say('NO AMMO'); return this.player.weapon; }
      this.player.weapon = index;
      return index;
    }

    fire() {
      const p = this.player;
      if (this.state !== 'playing' || p.fireCooldown > 0) return false;
      const w = WEAPONS[p.weapon];
      if (p[w.ammo] <= 0) {
        this._say('CLICK... NO AMMO');
        if (p.weapon !== 0) this.switchWeapon(1);
        return false;
      }
      p[w.ammo]--;
      p.fireCooldown = w.cooldown;
      this.muzzle = 0.09;
      this.crosshairPulse = 0.14;
      let hitAny = false;
      for (let pellet = 0; pellet < w.pellets; pellet++) {
        const spread = (pellet === 0 ? 0 : (Math.random() * 2 - 1) * w.spread);
        const hit = this._hitscan(p.yaw + spread, w.damage);
        if (hit) hitAny = true;
      }
      if (hitAny) this.crosshairPulse = 0.2;
      return true;
    }

    _hitscan(angle, damage) {
      const dx = Math.cos(angle), dy = Math.sin(angle);
      let best = null, bestDist = Infinity;
      for (const e of this.enemies) {
        if (!e.alive) continue;
        const ex = e.x - this.player.x, ey = e.y - this.player.y;
        const along = ex * dx + ey * dy;
        if (along <= 0) continue;
        const perp = Math.abs(ex * dy - ey * dx);
        if (perp > 0.38) continue;
        if (!this._lineOfSight(this.player.x, this.player.y, e.x, e.y)) continue;
        if (along < bestDist) { bestDist = along; best = e; }
      }
      if (!best) return false;
      best.hp -= damage;
      best.hurt = 0.12;
      this._spawnBlood(best.x, best.y);
      if (best.hp <= 0) {
        best.alive = false;
        this.kills++;
        this.player.bullets += best.kind === 'c' ? 6 : 3;
        this._say('TARGET DOWN');
      }
      return true;
    }

    nextLevel() {
      if (this.levelIndex + 1 >= this.levels.length) {
        this.state = 'victory';
        this._say('SECTOR CLEARED');
        return;
      }
      const health = this.player.health, armor = this.player.armor;
      const ammo = { bullets: this.player.bullets, shells: this.player.shells, cells: this.player.cells };
      this.reset(this.levelIndex + 1);
      Object.assign(this.player, ammo);
      this.player.health = health;
      this.player.armor = armor;
    }

    _say(text) { this.message = text; this.messageTimer = 1.8; }

    _spawnBlood(x, y) {
      for (let i = 0; i < 5; i++) {
        this.particles.push({ x, y, z: 0.4 + Math.random() * 0.5, vx: (Math.random() - 0.5) * 1.4,
          vy: (Math.random() - 0.5) * 1.4, life: 0.35 + Math.random() * 0.25,
          maxLife: 0.6, color: i % 2 ? '#d62828' : '#7a0c0c' });
      }
    }

    update(dt, input) {
      if (this.state !== 'playing') return;
      dt = clamp(dt || 0, 0, 0.05);
      const p = this.player;
      input = input || {};
      const run = !!input.run || !!input.forward > 1.3;
      p.run = !!input.run;
      const moveSpeed = (p.run ? 3.3 : 2.0) * dt;
      const strafeSpeed = (p.run ? 2.8 : 1.7) * dt;

      // Look: touch drag arrives as a yaw delta; keyboard arrows as turn.
      p.yaw += (input.turn || 0) * 2.5 * dt + (input.lookYaw || 0);
      if (input.lookPitch) p.pitch = clamp(p.pitch + input.lookPitch, -0.45, 0.45);
      p.pitch *= Math.pow(0.0005, dt);

      let fw = clamp(input.forward || 0, -1, 1);
      let st = clamp(input.strafe || 0, -1, 1);
      const len = Math.hypot(fw, st);
      if (len > 1) { fw /= len; st /= len; }
      const dirX = Math.cos(p.yaw), dirY = Math.sin(p.yaw);
      const rightX = -Math.sin(p.yaw), rightY = Math.cos(p.yaw);
      const nx = p.x + (dirX * fw * moveSpeed) + (rightX * st * strafeSpeed);
      const ny = p.y + (dirY * fw * moveSpeed) + (rightY * st * strafeSpeed);
      if (!this.blocked(nx, p.y)) p.x = nx;
      if (!this.blocked(p.x, ny)) p.y = ny;

      // Doors.
      for (const key of Object.keys(this.doors)) {
        const door = this.doors[key];
        if (door.opening && door.open < 1) door.open = Math.min(1, door.open + dt * 1.25);
      }

      // Pickups.
      for (const item of this.pickups) {
        if (item.taken || Math.hypot(item.x - p.x, item.y - p.y) > 0.48) continue;
        item.taken = true;
        if (item.kind === 'h') { p.health = Math.min(100, p.health + 25); this._say('+25 HEALTH'); }
        else if (item.kind === 'a') { p.bullets += 24; this._say('+24 BULLETS'); }
        else if (item.kind === 's') { p.shells += 8; this._say('+8 SHELLS'); }
        else if (item.kind === 'r') { p.armor = Math.min(100, p.armor + 35); this._say('+35 ARMOR'); }
      }

      // Enemies.
      for (const e of this.enemies) {
        if (!e.alive) continue;
        e.hurt = Math.max(0, e.hurt - dt);
        e.cooldown -= dt;
        const dx = p.x - e.x, dy = p.y - e.y;
        const dist = Math.hypot(dx, dy);
        if (dist > 13 || !this._lineOfSight(e.x, e.y, p.x, p.y)) continue;
        if (dist > (e.kind === 'c' ? 1.5 : 1.05)) {
          const step = e.speed * dt;
          const ex = e.x + (dx / (dist || 1)) * step;
          const ey = e.y + (dy / (dist || 1)) * step;
          if (!this.blocked(ex, e.y)) e.x = ex;
          if (!this.blocked(e.x, ey)) e.y = ey;
        } else if (e.cooldown <= 0) {
          e.cooldown = e.kind === 'c' ? 1.25 : 0.9;
          this._damagePlayer(e.kind === 'c' ? 16 : e.kind === 'z' ? 7 : 11);
        }
      }

      // Exit.
      if (Math.hypot(p.x - this.exit.x, p.y - this.exit.y) < 0.55) this.nextLevel();

      p.fireCooldown = Math.max(0, p.fireCooldown - dt);
      p.hurtTimer = Math.max(0, p.hurtTimer - dt);
      this.muzzle = Math.max(0, this.muzzle - dt);
      this.damageFlash = Math.max(0, this.damageFlash - dt * 2.2);
      this.crosshairPulse = Math.max(0, this.crosshairPulse - dt);
      this.messageTimer = Math.max(0, this.messageTimer - dt);
      for (const q of this.particles) {
        q.x += q.vx * dt; q.y += q.vy * dt; q.z -= dt * 1.6; q.life -= dt;
      }
      this.particles = this.particles.filter(q => q.life > 0);
      if (p.health <= 0) { p.health = 0; this.state = 'dead'; }
    }

    _damagePlayer(amount) {
      const p = this.player;
      const absorbed = Math.min(p.armor, Math.round(amount * 0.55));
      p.armor -= absorbed;
      p.health -= amount - absorbed;
      p.hurtTimer = 0.3;
      this.damageFlash = Math.min(1, this.damageFlash + 0.55);
      if (p.health <= 0) { p.health = 0; this.state = 'dead'; }
    }

    /* ---- rendering ------------------------------------------------------ */
    render(ctx) {
      const W = this.width, H = this.height;
      const p = this.player;
      const horizon = Math.floor(H * 0.5 + p.pitch * H);
      const ceiling = ctx.createLinearGradient(0, 0, 0, Math.max(1, horizon));
      ceiling.addColorStop(0, '#05070c');
      ceiling.addColorStop(1, '#21100d');
      ctx.fillStyle = ceiling;
      ctx.fillRect(0, 0, W, Math.max(1, horizon));
      const floor = ctx.createLinearGradient(0, horizon, 0, H);
      floor.addColorStop(0, '#3a2117');
      floor.addColorStop(1, '#0b0908');
      ctx.fillStyle = floor;
      ctx.fillRect(0, horizon, W, H - horizon);

      const dirX = Math.cos(p.yaw), dirY = Math.sin(p.yaw);
      const planeX = -dirY * 0.66, planeY = dirX * 0.66;
      const zBuffer = new Float32Array(W);
      for (let x = 0; x < W; x++) {
        const cameraX = 2 * x / W - 1;
        const rayX = dirX + planeX * cameraX;
        const rayY = dirY + planeY * cameraX;
        let mapX = Math.floor(p.x), mapY = Math.floor(p.y);
        const deltaX = Math.abs(1 / (rayX || 1e-9)), deltaY = Math.abs(1 / (rayY || 1e-9));
        let stepX, stepY, sideDistX, sideDistY;
        if (rayX < 0) { stepX = -1; sideDistX = (p.x - mapX) * deltaX; } else { stepX = 1; sideDistX = (mapX + 1 - p.x) * deltaX; }
        if (rayY < 0) { stepY = -1; sideDistY = (p.y - mapY) * deltaY; } else { stepY = 1; sideDistY = (mapY + 1 - p.y) * deltaY; }
        let side = 0, tile = 0, hit = false;
        for (let depth = 0; depth < 96; depth++) {
          if (sideDistX < sideDistY) { sideDistX += deltaX; mapX += stepX; side = 0; }
          else { sideDistY += deltaY; mapY += stepY; side = 1; }
          tile = this.tileAt(mapX + 0.01, mapY + 0.01);
          if (tile) { hit = true; break; }
        }
        if (!hit) { zBuffer[x] = 99; continue; }
        const perp = side === 0 ? (sideDistX - deltaX) : (sideDistY - deltaY);
        zBuffer[x] = perp;
        const wallH = Math.floor(H / Math.max(perp, 0.0001));
        const top = horizon - wallH / 2;
        const color = WALL_COLORS[tile] || WALL_COLORS[1];
        const shade = clamp(1.15 - perp / 13, 0.22, 1);
        ctx.fillStyle = side ? color.dark : color.light;
        ctx.globalAlpha = shade;
        ctx.fillRect(x, top, 1, wallH);
        ctx.globalAlpha = 1;
        if (tile === 4) {
          ctx.fillStyle = color.edge;
          ctx.fillRect(x, top, 1, 2);
          ctx.fillRect(x, top + wallH - 3, 1, 3);
        } else if (wallH > 18) {
          const wallX = side === 0 ? (p.y + perp * rayY) % 1 : (p.x + perp * rayX) % 1;
          if (wallX < 0.04) {
            ctx.globalAlpha = shade * 0.45;
            ctx.fillStyle = '#050505';
            ctx.fillRect(x, top, 1, wallH);
            ctx.globalAlpha = 1;
          }
        }
      }

      // Sprite billboards (enemies and pickups), back-to-front.
      const rx = -dirY, ry = dirX;
      const sprites = [];
      for (const e of this.enemies) if (e.alive) sprites.push({ x: e.x, y: e.y, kind: 'enemy', e });
      for (const item of this.pickups) if (!item.taken) sprites.push({ x: item.x, y: item.y, kind: 'item', item });
      sprites.push({ x: this.exit.x, y: this.exit.y, kind: 'exit' });
      const invDet = 1.0 / (planeX * dirY - dirX * planeY);
      for (const s of sprites) {
        const sx = s.x - p.x, sy = s.y - p.y;
        s.tx = invDet * (dirY * sx - dirX * sy);
        s.ty = invDet * (-planeY * sx + planeX * sy);
      }
      sprites.sort((a, b) => b.ty - a.ty);
      for (const s of sprites) {
        if (s.ty <= 0.12) continue;
        const screenX = Math.floor((W / 2) * (1 + s.tx / s.ty));
        const spriteH = s.kind === 'item' ? H / s.ty * 0.28 : s.kind === 'exit' ? H / s.ty * 0.8 : H / s.ty * 0.78;
        const spriteW = s.kind === 'item' ? spriteH : spriteH;
        const top = Math.floor(horizon - spriteH * 0.5);
        const left = Math.floor(screenX - spriteW / 2);
        if (screenX < -spriteW || screenX > W + spriteW) continue;
        if (s.kind === 'enemy') {
          const art = s.e.hurt > 0 ? this.sprites.enemyHurt[s.e.kind] : this.sprites.enemy[s.e.kind];
          if (art) this._blitSprite(ctx, art, left, top, spriteW, spriteH, zBuffer, screenX);
        } else if (s.kind === 'item') {
          const colors = { h: '#35d07f', a: '#ffd166', s: '#ff8c42', r: '#59a6ff' };
          ctx.fillStyle = colors[s.item.kind] || '#ffffff';
          ctx.fillRect(left + spriteW * 0.3, top + spriteH * 0.25, spriteW * 0.4, spriteH * 0.5);
          ctx.fillStyle = '#0b0b0b';
          ctx.fillRect(left + spriteW * 0.44, top + spriteH * 0.37, spriteW * 0.12, spriteH * 0.26);
        } else if (s.kind === 'exit') {
          ctx.strokeStyle = '#64ffda';
          ctx.lineWidth = Math.max(1, W / 240);
          ctx.strokeRect(left + spriteW * 0.24, top + spriteH * 0.12, spriteW * 0.52, spriteH * 0.76);
          ctx.fillStyle = 'rgba(100,255,218,.18)';
          ctx.fillRect(left + spriteW * 0.24, top + spriteH * 0.12, spriteW * 0.52, spriteH * 0.76);
        }
      }

      // Particles.
      for (const q of this.particles) {
        const sx = q.x - p.x, sy = q.y - p.y;
        const tx = invDet * (dirY * sx - dirX * sy);
        const ty = invDet * (-planeY * sx + planeX * sy);
        if (ty <= 0.15) continue;
        const px = (W / 2) * (1 + tx / ty);
        const py = horizon - (q.z - 0.5) * H / ty;
        const size = Math.max(1, H / ty * 0.04);
        ctx.fillStyle = q.color;
        ctx.globalAlpha = clamp(q.life / q.maxLife, 0, 1);
        ctx.fillRect(px, py, size, size);
      }
      ctx.globalAlpha = 1;

      this._renderWeapon(ctx, W, H);
      this._renderMinimap(ctx, W, H);
      this._renderCrosshair(ctx, W, H);

      if (this.damageFlash > 0) {
        ctx.fillStyle = 'rgba(190,20,10,' + (this.damageFlash * 0.42) + ')';
        ctx.fillRect(0, 0, W, H);
      }
      if (p.hurtTimer > 0) {
        ctx.strokeStyle = 'rgba(255,50,30,' + p.hurtTimer + ')';
        ctx.lineWidth = 3;
        ctx.strokeRect(1.5, 1.5, W - 3, H - 3);
      }
      if (this.messageTimer > 0) {
        ctx.font = 'bold 7px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = 'rgba(0,0,0,.55)';
        ctx.fillRect(W / 2 - 62, H - 33, 124, 11);
        ctx.fillStyle = '#ffd166';
        ctx.fillText(this.message, W / 2, H - 25);
        ctx.textAlign = 'left';
      }
    }

    _blitSprite(ctx, art, left, top, w, h, zBuffer, screenX) {
      const W = this.width;
      if (!isFinite(w) || !isFinite(h) || w <= 0 || h <= 0) return;
      const x0 = Math.max(0, Math.floor(left));
      const x1 = Math.min(W, Math.ceil(left + w));
      for (let x = x0; x < x1; x++) {
        if (zBuffer[x] < 0.12) continue;
        // Conservative depth test at the sprite centre keeps walls in front.
        const at = Math.floor(((x - left) / w) * art.width);
        if (at < 0 || at >= art.width) continue;
        if (zBuffer[x] < Math.abs((x - screenX) / Math.max(1, w)) * 0.0 + 0.01) continue;
        ctx.drawImage(art, at, 0, 1, art.height, x, top, 1, h);
      }
      // The per-column draw above lets wall columns stay visible; sprites are
      // intentionally clipped by the wall depth buffer.
    }

    _renderWeapon(ctx, W, H) {
      const p = this.player;
      const bob = Math.sin(performance.now() / 180) * (p.run ? 2.2 : 1.0);
      const baseY = H - 30 + bob;
      ctx.save();
      ctx.translate(W / 2, baseY);
      if (p.weapon === 0) {
        ctx.fillStyle = '#24262c'; ctx.fillRect(-10, -8, 20, 28);
        ctx.fillStyle = '#7b8898'; ctx.fillRect(-5, -22, 10, 22);
        ctx.fillStyle = '#c8d4e3'; ctx.fillRect(-3, -24, 6, 5);
      } else if (p.weapon === 1) {
        ctx.fillStyle = '#4a2a15'; ctx.fillRect(-26, 2, 52, 18);
        ctx.fillStyle = '#26262c'; ctx.fillRect(-14, -26, 28, 30);
        ctx.fillStyle = '#89939f'; ctx.fillRect(-9, -32, 18, 14);
      } else {
        ctx.fillStyle = '#15343d'; ctx.fillRect(-16, -8, 32, 24);
        ctx.fillStyle = '#48e0ff'; ctx.fillRect(-11, -20, 22, 16);
        ctx.fillStyle = '#b8f7ff'; ctx.fillRect(-4, -28, 8, 10);
      }
      if (this.muzzle > 0) {
        ctx.fillStyle = '#fff3b0';
        ctx.beginPath();
        ctx.moveTo(-12, -30); ctx.lineTo(0, -48); ctx.lineTo(12, -30); ctx.closePath();
        ctx.fill();
        ctx.fillStyle = '#ff9d3b';
        ctx.beginPath();
        ctx.moveTo(-6, -28); ctx.lineTo(0, -40); ctx.lineTo(6, -28); ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
      // HUD strip.
      ctx.fillStyle = 'rgba(4,7,10,.82)';
      ctx.fillRect(0, H - 18, W, 18);
      ctx.fillStyle = '#ff7a2f';
      ctx.fillRect(0, H - 18, W, 1);
      ctx.font = 'bold 7px monospace';
      ctx.fillStyle = '#f4f1de';
      ctx.fillText('HP ' + String(Math.ceil(p.health)).padStart(3, ' '), 7, H - 6);
      ctx.fillStyle = '#59a6ff';
      ctx.fillText('AR ' + String(Math.ceil(p.armor)).padStart(3, ' '), 62, H - 6);
      ctx.fillStyle = '#ffd166';
      const w = WEAPONS[p.weapon];
      ctx.fillText(w.name + ' ' + String(p[w.ammo]).padStart(2, '0'), 117, H - 6);
      ctx.fillStyle = '#64ffda';
      ctx.fillText('K ' + this.kills + '/' + this.totalEnemies, W - 52, H - 6);
    }

    _renderMinimap(ctx, W, H) {
      const size = Math.min(52, W * 0.16);
      const cell = size / this.mapW;
      const ox = W - size - 5, oy = 8;
      ctx.fillStyle = 'rgba(0,0,0,.45)';
      ctx.fillRect(ox - 2, oy - 2, size + 4, size + 4);
      for (let y = 0; y < this.mapH; y++) {
        for (let x = 0; x < this.mapW; x++) {
          const t = this.tileAt(x + 0.5, y + 0.5);
          if (!t) continue;
          ctx.fillStyle = t === 4 ? '#ffb347' : 'rgba(180,120,90,.7)';
          ctx.fillRect(ox + x * cell, oy + y * cell, Math.ceil(cell), Math.ceil(cell));
        }
      }
      ctx.fillStyle = '#64ffda';
      ctx.fillRect(ox + this.player.x * cell - 1, oy + this.player.y * cell - 1, 2, 2);
      ctx.fillStyle = '#ff5d5d';
      for (const e of this.enemies) if (e.alive) ctx.fillRect(ox + e.x * cell, oy + e.y * cell, 1, 1);
    }

    _renderCrosshair(ctx, W, H) {
      const pulse = this.crosshairPulse > 0 ? 1.6 : 0;
      const cx = W / 2, cy = H / 2;
      ctx.strokeStyle = this.crosshairPulse > 0 ? '#ffd166' : 'rgba(255,255,255,.78)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx - 4 - pulse, cy); ctx.lineTo(cx - 1, cy);
      ctx.moveTo(cx + 1, cy); ctx.lineTo(cx + 4 + pulse, cy);
      ctx.moveTo(cx, cy - 4 - pulse); ctx.lineTo(cx, cy - 1);
      ctx.moveTo(cx, cy + 1); ctx.lineTo(cx, cy + 4 + pulse);
      ctx.stroke();
    }

    snapshot() {
      const p = this.player;
      return {
        state: this.state, level: this.levelIndex + 1, levels: this.levels.length,
        health: Math.ceil(p.health), armor: Math.ceil(p.armor),
        weapon: WEAPONS[p.weapon].id, ammo: p[WEAPONS[p.weapon].ammo],
        bullets: p.bullets, shells: p.shells, cells: p.cells,
        kills: this.kills, enemies: this.totalEnemies, message: this.message,
      };
    }
  }

  DoomEngine.LEVELS = [
    {
      name: 'SECTOR 01 — DOCKING BAY',
      map: [
        '################',
        '#P.....#.......#',
        '#.###..#.#####.#',
        '#...#..D...#...#',
        '###.#..#...#.#.#',
        '#...#..###.#.#.#',
        '#.i.#......#...#',
        '#...#.#####.###D',
        '#.h.#.#...#...X#',
        '#...#.#.z.#.#####',
        '#.###.#...#.....#',
        '#.....#.#####.#.#',
        '#.a...#...i...#.#',
        '#.###.#####.#.#.#',
        '#...........#...#',
        '################',
      ],
    },
    {
      name: 'SECTOR 02 — FOUNDRY',
      map: [
        '################',
        '#P..#.....#....#',
        '#.#.#.###.#.##.#',
        '#.#...#z#...#..#',
        '#.#####.#.###.##',
        '#...s...#...i..#',
        '###.#####.######',
        '#...#...#......#',
        '#.#.#.#.#####.##',
        '#.#...#.....#..#',
        '#.#####.###.#.##',
        '#.....#...#.#..#',
        '#.###.#.c.#.#..#',
        '#...#.#...#.##.#',
        '#X..#.....#....#',
        '################',
      ],
    },
    {
      name: 'SECTOR 03 — HELLGATE',
      map: [
        '################',
        '#P....#....#...#',
        '#.###.#.##.#.#.#',
        '#.#...#..#...#.#',
        '#.#.####.###.#.#',
        '#...#..c...#.#.#',
        '###.#.#####.#.##',
        '#...#.#...#.#..#',
        '#.###.#.z.#.##.#',
        '#.....#...#....#',
        '#####.###.######',
        '#...#...#......#',
        '#.#.#.#.###.##.#',
        '#.#...#...i.#..#',
        '#X#########....#',
        '################',
      ],
    },
  ];

  global.NuxelDoomEngine = DoomEngine;
  global.NuxelDoomWeapons = WEAPONS;
})(typeof window !== 'undefined' ? window : globalThis);
