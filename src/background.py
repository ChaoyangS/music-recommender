import streamlit.components.v1 as components


def inject_floating_background() -> None:
    components.html("""
<script>
(function () {
    var doc = window.parent.document;
    if (doc.getElementById('music-bg')) return;

    // ── Shared audio context ──────────────────────────────────────────────────
    var audioCtx = null;
    function getAudioCtx() {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        return audioCtx;
    }
    function playPop() {
        if (!bgEnabled) return;
        try {
            var ctx = getAudioCtx();
            var osc  = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(700, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(180, ctx.currentTime + 0.18);
            gain.gain.setValueAtTime(0.28, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.18);
        } catch(e) {}
    }

    // ── Persist on/off state ──────────────────────────────────────────────────
    var bgEnabled = (window.parent.localStorage.getItem('musicBgEnabled') !== 'false');

    // ── CSS ───────────────────────────────────────────────────────────────────
    var style = doc.createElement('style');
    style.id = 'music-bg-style';
    style.textContent = `
        #music-bg {
            position: fixed;
            inset: 0;
            z-index: 1;
            overflow: hidden;
            pointer-events: none;
        }
        #music-bg.hidden { display: none; }
        .music-note {
            position: absolute;
            opacity: 0;
            animation: floatNote linear infinite;
            user-select: none;
            pointer-events: all;
            cursor: default;
        }
        .music-note:hover { animation-play-state: paused; }
        @keyframes popBurst {
            0%   { transform: scale(1)   rotate(0deg);   opacity: 0.7; }
            35%  { transform: scale(2.2) rotate(-12deg); opacity: 0.9; }
            70%  { transform: scale(1.6) rotate(8deg);   opacity: 0.4; }
            100% { transform: scale(0)   rotate(15deg);  opacity: 0;   }
        }
        @keyframes floatNote {
            0%   { transform: translateY(105vh) rotate(-8deg);  opacity: 0;   }
            8%   { opacity: 0.7; }
            85%  { opacity: 0.55; }
            100% { transform: translateY(-10vh) rotate(15deg);  opacity: 0;   }
        }
        .music-bar {
            position: absolute;
            bottom: 0;
            display: flex;
            align-items: flex-end;
            gap: 4px;
        }
        .music-bar span {
            display: inline-block;
            width: 5px;
            background: #BF5A34;
            border-radius: 2px 2px 0 0;
            opacity: 0.45;
            animation: barPulse ease-in-out infinite alternate;
            transform-origin: bottom;
        }
        @keyframes barPulse {
            from { transform: scaleY(0.2); }
            to   { transform: scaleY(1.0); }
        }
        #music-bg-btn {
            position: fixed;
            bottom: 22px;
            right: 22px;
            z-index: 9999;
            width: 34px;
            height: 34px;
            background: transparent;
            border: 1px solid #6B5C4A;
            color: #BF5A34;
            font-size: 17px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: border-color 0.15s, color 0.15s, opacity 0.15s;
            border-radius: 0;
            padding: 0;
            line-height: 1;
        }
        #music-bg-btn:hover { border-color: #BF5A34; color: #EAE0CC; }
        #music-bg-btn.off   { color: #3a3028; border-color: #2e2620; }
        #music-bg-btn .slash {
            position: absolute;
            width: 1px;
            height: 22px;
            background: #6B5C4A;
            transform: rotate(45deg);
            display: none;
        }
        #music-bg-btn.off .slash { display: block; }
    `;
    doc.head.appendChild(style);

    // ── Toggle button ─────────────────────────────────────────────────────────
    var btn = doc.createElement('button');
    btn.id = 'music-bg-btn';
    btn.title = 'Toggle music background';
    btn.innerHTML = '♪<span class="slash"></span>';
    if (!bgEnabled) btn.classList.add('off');
    btn.addEventListener('click', function() {
        bgEnabled = !bgEnabled;
        window.parent.localStorage.setItem('musicBgEnabled', bgEnabled);
        bg.classList.toggle('hidden', !bgEnabled);
        btn.classList.toggle('off', !bgEnabled);
    });
    doc.body.appendChild(btn);

    // ── Icons ─────────────────────────────────────────────────────────────────
    var icons = {
        note1: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 46" width="34" height="46"><g stroke="#BF5A34" stroke-width="2.3" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M7 37 C4 34 4 29 8 28 C13 27 18 30 17 35 C16 39 11 40 7 37Z" fill="rgba(191,90,52,0.28)"/><path d="M17 33 L18 6"/><path d="M18 6 C25 9 27 18 20 23"/></g></svg>',
        note2: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 54 46" width="54" height="46"><g stroke="#BF5A34" stroke-width="2.3" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M6 38 C3 35 3 30 7 29 C12 28 17 31 16 36 C15 40 10 41 6 38Z" fill="rgba(191,90,52,0.28)"/><path d="M37 34 C34 31 34 26 38 25 C43 24 48 27 47 32 C46 36 41 37 37 34Z" fill="rgba(191,90,52,0.28)"/><path d="M16 34 L17 7"/><path d="M47 30 L48 7"/><path d="M17 7 L48 7"/></g></svg>',
        headphones: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 46 40" width="46" height="40"><g stroke="#BF5A34" stroke-width="2.3" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M7 22 C6 10 14 4 23 4 C32 4 40 10 39 22"/><path d="M3 21 C3 19 5 18 7 19 L7 32 C5 33 3 32 3 30 Z" fill="rgba(191,90,52,0.25)"/><path d="M43 21 C43 19 41 18 39 19 L39 32 C41 33 43 32 43 30 Z" fill="rgba(191,90,52,0.25)"/></g></svg>',
        guitar: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 56" width="30" height="56"><g stroke="#BF5A34" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M15 27 C9 27 4 31 4 37 C4 43 9 48 15 48 C21 48 26 43 26 37 C26 31 21 27 15 27Z" fill="rgba(191,90,52,0.2)"/><circle cx="15" cy="37" r="3.5" fill="rgba(191,90,52,0.35)" stroke="#BF5A34" stroke-width="1.5"/><path d="M15 27 L15 7"/><path d="M11 7 L19 7"/><path d="M10 11 L20 11"/><path d="M10 31 Q15 29 20 31"/></g></svg>',
        mic: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 52" width="30" height="52"><g stroke="#BF5A34" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M10 5 C10 3 20 3 20 5 L20 23 C20 25 10 25 10 23 Z" fill="rgba(191,90,52,0.22)"/><path d="M7 14 C7 8 10 6 15 6"/><path d="M5 17 C5 27 25 27 25 17"/><path d="M15 27 L15 40"/><path d="M9 40 L21 40"/><path d="M11 10 L19 10"/><path d="M11 15 L19 15"/><path d="M11 20 L19 20"/></g></svg>',
        wave: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 30" width="52" height="30"><g stroke="#BF5A34" stroke-width="2.3" fill="none" stroke-linecap="round"><path d="M2 9 C7 5 10 13 15 9 C20 5 23 13 28 9 C33 5 36 13 41 9 C44 6 47 10 50 9"/><path d="M2 17 C8 12 11 22 16 17 C21 12 24 22 29 17 C34 12 37 22 42 17 C45 14 48 19 50 17"/><path d="M2 25 C6 22 10 28 15 25 C19 22 23 28 28 25 C32 22 36 28 41 25 C44 23 47 26 50 25"/></g></svg>',
    };

    var items = [
        {key:'note1',      left:'4%',  dur:'13s', delay:'0s',   w:34, h:46},
        {key:'note2',      left:'11%', dur:'17s', delay:'2.5s', w:54, h:46},
        {key:'headphones', left:'20%', dur:'11s', delay:'5s',   w:46, h:40},
        {key:'guitar',     left:'30%', dur:'20s', delay:'1s',   w:30, h:56},
        {key:'mic',        left:'40%', dur:'14s', delay:'7s',   w:30, h:52},
        {key:'wave',       left:'50%', dur:'10s', delay:'3.5s', w:52, h:30},
        {key:'note1',      left:'59%', dur:'18s', delay:'0.5s', w:28, h:38},
        {key:'note2',      left:'67%', dur:'12s', delay:'6s',   w:44, h:38},
        {key:'headphones', left:'75%', dur:'16s', delay:'4s',   w:38, h:33},
        {key:'guitar',     left:'83%', dur:'21s', delay:'2s',   w:24, h:45},
        {key:'mic',        left:'91%', dur:'11s', delay:'8s',   w:24, h:42},
        {key:'wave',       left:'8%',  dur:'23s', delay:'10s',  w:42, h:24},
        {key:'note1',      left:'47%', dur:'9s',  delay:'9s',   w:40, h:54},
        {key:'guitar',     left:'72%', dur:'25s', delay:'12s',  w:26, h:48},
        {key:'headphones', left:'35%', dur:'15s', delay:'4.5s', w:42, h:36},
    ];

    var bg = doc.createElement('div');
    bg.id = 'music-bg';
    if (!bgEnabled) bg.classList.add('hidden');

    items.forEach(function(n) {
        var el = doc.createElement('div');
        el.className = 'music-note';
        el.innerHTML = icons[n.key];
        el.style.cssText = 'left:' + n.left + ';width:' + n.w + 'px;height:' + n.h + 'px' +
            ';animation-duration:' + n.dur + ';animation-delay:' + n.delay;
        el.addEventListener('click', function(e) {
            playPop();
            var burst = doc.createElement('div');
            burst.innerHTML = icons[n.key];
            burst.style.cssText = [
                'position:fixed',
                'left:' + (e.clientX - n.w / 2) + 'px',
                'top:'  + (e.clientY - n.h / 2) + 'px',
                'width:'  + n.w + 'px',
                'height:' + n.h + 'px',
                'z-index:9998',
                'pointer-events:none',
                'animation:popBurst 0.45s cubic-bezier(0.36,0.07,0.19,0.97) forwards',
            ].join(';');
            doc.body.appendChild(burst);
            burst.addEventListener('animationend', function() { burst.remove(); });
            el.style.animation = 'none';
            el.getBoundingClientRect();
            el.style.animation = '';
        });
        bg.appendChild(el);
    });

    var barL = doc.createElement('div');
    barL.className = 'music-bar';
    barL.style.cssText = 'left:2%;height:100px';
    [50,70,30,80,45,65,35,75,55,40].forEach(function(h, i) {
        var s = doc.createElement('span');
        s.style.cssText = 'height:' + h + 'px;animation-duration:' + (0.6 + i*0.07).toFixed(2) + 's;animation-delay:' + (i*0.1).toFixed(1) + 's';
        barL.appendChild(s);
    });
    bg.appendChild(barL);

    var barR = doc.createElement('div');
    barR.className = 'music-bar';
    barR.style.cssText = 'right:2%;height:100px';
    [40,75,25,85,50,60,35,70,45,80].forEach(function(h, i) {
        var s = doc.createElement('span');
        s.style.cssText = 'height:' + h + 'px;animation-duration:' + (0.65 + i*0.06).toFixed(2) + 's;animation-delay:' + (i*0.12).toFixed(2) + 's';
        barR.appendChild(s);
    });
    bg.appendChild(barR);

    doc.body.appendChild(bg);
})();
</script>
""", height=0)
