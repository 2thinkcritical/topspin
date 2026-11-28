// A ball bounces across the tops of the title's letters, drops onto the
// baseline after the last one and comes to rest there.
"use strict";

(() => {
  const title = document.getElementById("club-title");
  if (!title) return;

  const START_DELAY_MS = 500;
  const EASE_OUT = "cubic-bezier(.25,.46,.45,.94)"; // rising
  const EASE_IN = "cubic-bezier(.55,.085,.68,.53)"; // falling

  // Wrap every character in a span so each letter can be measured.
  const letters = [];
  (function split(node) {
    for (const child of [...node.childNodes]) {
      if (child.nodeType !== Node.TEXT_NODE) {
        split(child);
        continue;
      }
      const fragment = document.createDocumentFragment();
      for (const char of child.textContent) {
        const span = document.createElement("span");
        span.textContent = char;
        span.setAttribute("aria-hidden", "true");
        if (char.trim()) letters.push(span);
        fragment.append(span);
      }
      child.replaceWith(fragment);
    }
  })(title);
  if (!letters.length) return;

  // An empty inline-block sits on the text baseline, which lets us find it.
  const baseline = document.createElement("span");
  baseline.className = "title-baseline";
  const ball = document.createElement("span");
  ball.className = "hop-ball";
  ball.setAttribute("aria-hidden", "true");
  const body = document.createElement("i");
  ball.append(body);
  title.append(baseline, ball);

  let animations = [];

  function geometry() {
    const box = title.getBoundingClientRect();
    const style = getComputedStyle(title);
    const fontSize = parseFloat(style.fontSize);
    const context = document.createElement("canvas").getContext("2d");
    context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const capHeight = context.measureText("K").actualBoundingBoxAscent || fontSize * 0.72;
    const lineToBaseline =
      baseline.getBoundingClientRect().top - letters.at(-1).getBoundingClientRect().bottom;
    const diameter = Math.max(10, Math.round(fontSize * 0.3));
    const radius = diameter / 2;
    ball.style.setProperty("--d", `${diameter}px`);

    const tops = letters.map((letter) => {
      const r = letter.getBoundingClientRect();
      return {
        x: r.left - box.left + r.width / 2,
        y: r.bottom + lineToBaseline - box.top - capHeight - radius,
        right: r.right - box.left,
      };
    });
    const last = tops.at(-1);
    const rest = { x: last.right + radius + fontSize * 0.35, y: last.y + capHeight };
    return { tops, rest, fontSize };
  }

  function placeAt({ x, y }) {
    animations.forEach((a) => a.cancel());
    animations = [];
    ball.style.opacity = 1;
    ball.style.transform = `translateX(${x}px)`;
    body.style.transform = `translateY(${y}px)`;
  }

  // Horizontal motion is linear and vertical motion follows gravity, so the two
  // axes are animated on nested elements with shared keyframe times.
  function play() {
    const { tops, rest, fontSize } = geometry();
    const hopHeight = fontSize * 0.55;
    const msPerSqrtPx = 135 / Math.sqrt(hopHeight); // fall time grows with sqrt(height)
    const xFrames = [];
    const yFrames = [];
    let time = 0;
    let at;

    const key = (x, y, easing, opacity = 1) => {
      xFrames.push({ time, transform: `translateX(${x}px)`, opacity });
      yFrames.push({ time, transform: `translateY(${y}px)`, easing });
      at = { x, y };
    };
    const hop = (to, height) => {
      const peak = Math.min(at.y, to.y) - height;
      const up = msPerSqrtPx * Math.sqrt(at.y - peak);
      const down = msPerSqrtPx * Math.sqrt(to.y - peak);
      const from = at.x;
      time += up;
      key(from + ((to.x - from) * up) / (up + down), peak, EASE_IN);
      time += down;
      key(to.x, to.y, EASE_OUT);
    };

    const [first, ...others] = tops;
    key(first.x - fontSize * 1.4, first.y - hopHeight * 2.2, EASE_IN, 0); // enters from the upper left
    time += msPerSqrtPx * Math.sqrt(hopHeight * 2.2);
    key(first.x, first.y, EASE_OUT);
    others.forEach((top) => hop(top, hopHeight));
    hop(rest, hopHeight * 0.8); // drops onto the baseline
    const step = fontSize * 0.18;
    hop({ x: rest.x + step, y: rest.y }, hopHeight * 0.3); // two dying bounces
    hop({ x: rest.x + step * 1.5, y: rest.y }, hopHeight * 0.1);

    const duration = time;
    const toKeyframes = (frames) =>
      frames.map(({ time: t, ...frame }) => ({ ...frame, offset: t / duration }));
    ball.style.opacity = "";
    animations = [
      ball.animate(toKeyframes(xFrames), { duration, fill: "forwards" }),
      body.animate(toKeyframes(yFrames), { duration, fill: "forwards" }),
    ];
    const end = at;
    animations[0].onfinish = () => placeAt(end);
  }

  function start() {
    const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion || !ball.animate) placeAt(geometry().rest);
    else play();

    // Re-measure when the width changes (not when a mobile toolbar hides).
    let width = innerWidth;
    addEventListener("resize", () => {
      if (innerWidth === width) return;
      width = innerWidth;
      placeAt(geometry().rest);
    });
  }

  document.fonts.ready.then(() => setTimeout(start, START_DELAY_MS));
})();
