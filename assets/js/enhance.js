/* enhance.js — subtle, reduced-motion-aware page motion.
   Scroll-reveals elements with .reveal; runs independently of the
   Strata theme's preload handling so it never waits on image load. */
(function () {
	'use strict';

	var reduce = window.matchMedia &&
		window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	function revealAll(els) {
		for (var i = 0; i < els.length; i++) els[i].classList.add('is-visible');
	}

	function initReveals() {
		var els = document.querySelectorAll('.reveal');
		if (!els.length) return;

		if (reduce || !('IntersectionObserver' in window)) {
			revealAll(els);
			return;
		}

		var io = new IntersectionObserver(function (entries) {
			entries.forEach(function (entry) {
				if (entry.isIntersecting) {
					entry.target.classList.add('is-visible');
					io.unobserve(entry.target);
				}
			});
		}, { threshold: 0.05, rootMargin: '0px 0px 12% 0px' });

		els.forEach(function (el) { io.observe(el); });
	}

	function start() {
		// Don't wait for full window load (the portrait is heavy); enable
		// transitions early so above-the-fold reveals still animate.
		document.body.classList.remove('is-preload');
		document.body.classList.add('is-ready');
		initReveals();
	}

	// Run directly (no requestAnimationFrame, which is paused in background
	// tabs) so reveals never get stuck hidden. The IntersectionObserver
	// callback is itself async, so above-the-fold items still transition in.
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', start);
	} else {
		start();
	}
})();
