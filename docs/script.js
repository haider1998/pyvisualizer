/**
 * PyVisualizer Website JavaScript
 * Handles interactions, animations, and theme switching
 */

(function () {
    'use strict';

    // ============================================
    // Theme Management
    // ============================================
    const ThemeManager = {
        init() {
            this.toggle = document.getElementById('themeToggle');
            this.body = document.body;

            // Check for saved preference or system preference
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

            if (savedTheme) {
                this.setTheme(savedTheme);
            } else if (prefersDark) {
                this.setTheme('dark');
            }

            // Listen for toggle clicks
            if (this.toggle) {
                this.toggle.addEventListener('click', () => this.toggleTheme());
            }

            // Listen for system preference changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        },

        setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        },

        toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            this.setTheme(newTheme);
        }
    };

    // ============================================
    // Mobile Navigation
    // ============================================
    const MobileNav = {
        init() {
            this.toggle = document.getElementById('navToggle');
            this.menu = document.getElementById('navMenu');

            if (this.toggle && this.menu) {
                this.toggle.addEventListener('click', () => this.toggleMenu());

                // Close menu when clicking a link
                this.menu.querySelectorAll('a').forEach(link => {
                    link.addEventListener('click', () => this.closeMenu());
                });

                // Close menu when clicking outside
                document.addEventListener('click', (e) => {
                    if (!this.toggle.contains(e.target) && !this.menu.contains(e.target)) {
                        this.closeMenu();
                    }
                });
            }
        },

        toggleMenu() {
            this.toggle.classList.toggle('open');
            this.menu.classList.toggle('open');
            document.body.style.overflow = this.menu.classList.contains('open') ? 'hidden' : '';
        },

        closeMenu() {
            this.toggle.classList.remove('open');
            this.menu.classList.remove('open');
            document.body.style.overflow = '';
        }
    };

    // ============================================
    // Copy to Clipboard
    // ============================================
    const CopyButtons = {
        init() {
            document.querySelectorAll('.copy-btn').forEach(btn => {
                btn.addEventListener('click', () => this.handleCopy(btn));
            });
        },

        async handleCopy(btn) {
            const text = btn.dataset.copy;

            try {
                await navigator.clipboard.writeText(text);
                this.showSuccess(btn);
            } catch (err) {
                // Fallback for older browsers
                this.fallbackCopy(text);
                this.showSuccess(btn);
            }
        },

        fallbackCopy(text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        },

        showSuccess(btn) {
            btn.classList.add('copied');
            setTimeout(() => btn.classList.remove('copied'), 2000);
        }
    };

    // ============================================
    // Smooth Scroll
    // ============================================
    const SmoothScroll = {
        init() {
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', (e) => {
                    const targetId = anchor.getAttribute('href');
                    if (targetId === '#') return;

                    const target = document.querySelector(targetId);
                    if (target) {
                        e.preventDefault();
                        const navHeight = document.querySelector('.nav').offsetHeight;
                        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;

                        window.scrollTo({
                            top: targetPosition,
                            behavior: 'smooth'
                        });
                    }
                });
            });
        }
    };

    // ============================================
    // Scroll Animations
    // ============================================
    const ScrollAnimations = {
        init() {
            this.elements = document.querySelectorAll('.animate-on-scroll');

            if ('IntersectionObserver' in window) {
                this.observer = new IntersectionObserver(
                    (entries) => this.handleIntersect(entries),
                    {
                        threshold: 0.1,
                        rootMargin: '0px 0px -50px 0px'
                    }
                );

                this.elements.forEach(el => this.observer.observe(el));
            } else {
                // Fallback: show all elements
                this.elements.forEach(el => el.classList.add('visible'));
            }
        },

        handleIntersect(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    this.observer.unobserve(entry.target);
                }
            });
        }
    };

    // ============================================
    // Navigation Scroll Effect
    // ============================================
    const NavScroll = {
        init() {
            this.nav = document.getElementById('nav');
            this.lastScrollY = 0;

            window.addEventListener('scroll', () => this.handleScroll(), { passive: true });
        },

        handleScroll() {
            const currentScrollY = window.scrollY;

            // Add shadow on scroll
            if (currentScrollY > 10) {
                this.nav.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
            } else {
                this.nav.style.boxShadow = 'none';
            }

            this.lastScrollY = currentScrollY;
        }
    };

    // ============================================
    // Active Section Highlighting
    // ============================================
    const ActiveSection = {
        init() {
            this.sections = document.querySelectorAll('section[id]');
            this.navLinks = document.querySelectorAll('.nav-menu a[href^="#"]');

            if (this.sections.length && this.navLinks.length) {
                window.addEventListener('scroll', () => this.handleScroll(), { passive: true });
            }
        },

        handleScroll() {
            const scrollY = window.scrollY;
            const navHeight = document.querySelector('.nav').offsetHeight;

            this.sections.forEach(section => {
                const sectionTop = section.offsetTop - navHeight - 100;
                const sectionBottom = sectionTop + section.offsetHeight;
                const sectionId = section.getAttribute('id');

                if (scrollY >= sectionTop && scrollY < sectionBottom) {
                    this.navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === `#${sectionId}`) {
                            link.classList.add('active');
                        }
                    });
                }
            });
        }
    };

    // ============================================
    // Performance: Lazy load iframe
    // ============================================
    const LazyIframe = {
        init() {
            const iframe = document.querySelector('.demo-content iframe');
            if (!iframe) return;

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const src = iframe.getAttribute('src');
                        if (src) {
                            iframe.src = src; // Trigger load
                        }
                        observer.unobserve(iframe);
                    }
                });
            }, { rootMargin: '200px' });

            observer.observe(iframe);
        }
    };

    // ============================================
    // Initialize Everything
    // ============================================
    document.addEventListener('DOMContentLoaded', () => {
        ThemeManager.init();
        MobileNav.init();
        CopyButtons.init();
        SmoothScroll.init();
        ScrollAnimations.init();
        NavScroll.init();
        ActiveSection.init();
        LazyIframe.init();
    });

})();
