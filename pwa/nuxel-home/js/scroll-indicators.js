/* A39: lightweight noninteractive, 1 CSS-pixel touch-scroll indicators. */
(function () {
    'use strict';
    let vertical, horizontal, active, raf = 0, hideTimer;
    const ensure = () => {
        if (vertical) return;
        vertical = document.createElement('div'); horizontal = document.createElement('div');
        vertical.className = 'nuxel-scroll-indicator vertical';
        horizontal.className = 'nuxel-scroll-indicator horizontal';
        vertical.hidden = horizontal.hidden = true;
        document.body.append(vertical, horizontal);
    };
    const update = () => {
        raf = 0; ensure();
        const element = active;
        if (!element || !document.body.contains(element)) { vertical.hidden = horizontal.hidden = true; return; }
        const box = element.getBoundingClientRect();
        const visibleHeight = Math.min(element.clientHeight, innerHeight - Math.max(0, box.top));
        const visibleWidth = Math.min(element.clientWidth, innerWidth - Math.max(0, box.left));
        const vy = element.scrollHeight - element.clientHeight;
        const vx = element.scrollWidth - element.clientWidth;
        if (vy > 2 && visibleHeight > 0) {
            const height = Math.max(8, Math.floor(visibleHeight * element.clientHeight / element.scrollHeight));
            vertical.hidden = false;
            vertical.style.cssText = 'position:fixed;pointer-events:none;width:1px;z-index:120;' +
                'height:' + height + 'px;top:' + (box.top + (visibleHeight - height) * element.scrollTop / vy) + 'px;left:' + (box.right - 2) + 'px';
        } else vertical.hidden = true;
        if (vx > 2 && visibleWidth > 0) {
            const width = Math.max(8, Math.floor(visibleWidth * element.clientWidth / element.scrollWidth));
            horizontal.hidden = false;
            horizontal.style.cssText = 'position:fixed;pointer-events:none;height:1px;z-index:120;' +
                'width:' + width + 'px;left:' + (box.left + (visibleWidth - width) * element.scrollLeft / vx) + 'px;top:' + (box.bottom - 2) + 'px';
        } else horizontal.hidden = true;
    };
    function schedule() { if (!raf) raf = requestAnimationFrame(update); }
    document.addEventListener('scroll', event => {
        if (!(event.target instanceof Element)) return;
        active = event.target; schedule();
        clearTimeout(hideTimer);
        hideTimer = setTimeout(() => { vertical.hidden = horizontal.hidden = true; }, 1400);
    }, {passive:true, capture:true});
    window.addEventListener('resize', schedule, {passive:true});
})();
