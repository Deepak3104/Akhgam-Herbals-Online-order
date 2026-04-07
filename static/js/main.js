// ============================================
// Akhgam Herbals - Main JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function () {

    // ---------- Header Scroll Effect ----------
    const header = document.querySelector('.header');
    if (header) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }

    // ---------- Mobile Menu Toggle ----------
    const mobileToggle = document.querySelector('.mobile-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const mobileClose = document.querySelector('.mobile-close');

    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', function () {
            navMenu.classList.toggle('show');
            document.body.style.overflow = navMenu.classList.contains('show') ? 'hidden' : '';
        });
    }

    if (mobileClose && navMenu) {
        mobileClose.addEventListener('click', function () {
            navMenu.classList.remove('show');
            document.body.style.overflow = '';
        });
    }

    // ---------- User Dropdown Toggle ----------
    const userDropdown = document.getElementById('userDropdown');
    const userDropdownBtn = document.getElementById('userDropdownBtn');
    if (userDropdown && userDropdownBtn) {
        userDropdownBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            userDropdown.classList.toggle('open');
        });
        document.addEventListener('click', function (e) {
            if (!userDropdown.contains(e.target)) {
                userDropdown.classList.remove('open');
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') userDropdown.classList.remove('open');
        });
    }

    // ---------- Admin Profile Dropdown ----------
    const adminDropdown = document.getElementById('adminProfileDropdown');
    const adminDropdownBtn = document.getElementById('adminProfileBtn');
    if (adminDropdown && adminDropdownBtn) {
        adminDropdownBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            adminDropdown.classList.toggle('open');
        });
        document.addEventListener('click', function (e) {
            if (!adminDropdown.contains(e.target)) {
                adminDropdown.classList.remove('open');
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') adminDropdown.classList.remove('open');
        });
    }

    // ---------- Admin Mobile Navigation ----------
    const adminNav = document.getElementById('adminNav');
    const adminNavToggle = document.getElementById('adminNavToggle');
    const adminNavClose = document.getElementById('adminNavClose');
    const adminNavBackdrop = document.getElementById('adminNavBackdrop');

    function closeAdminNav() {
        if (!adminNav) return;
        adminNav.classList.remove('show');
        document.body.classList.remove('admin-nav-open');
        if (adminNavToggle) adminNavToggle.setAttribute('aria-expanded', 'false');
    }

    function openAdminNav() {
        if (!adminNav) return;
        adminNav.classList.add('show');
        document.body.classList.add('admin-nav-open');
        if (adminNavToggle) adminNavToggle.setAttribute('aria-expanded', 'true');
    }

    if (adminNav && adminNavToggle) {
        adminNavToggle.addEventListener('click', function () {
            if (adminNav.classList.contains('show')) {
                closeAdminNav();
            } else {
                openAdminNav();
            }
        });

        if (adminNavClose) {
            adminNavClose.addEventListener('click', closeAdminNav);
        }

        if (adminNavBackdrop) {
            adminNavBackdrop.addEventListener('click', closeAdminNav);
        }

        adminNav.querySelectorAll('.admin-nav-link').forEach(function (link) {
            link.addEventListener('click', function () {
                if (window.innerWidth <= 768) {
                    closeAdminNav();
                }
            });
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeAdminNav();
            }
        });
    }

    // ---------- Delete Account Modal ----------
    const deleteModal = document.getElementById('deleteAccountModal');
    const deleteForm = document.getElementById('deleteAccountForm');
    if (deleteModal && deleteForm) {
        // Close on overlay click
        deleteModal.addEventListener('click', function (e) {
            if (e.target === deleteModal) {
                deleteModal.classList.remove('show');
            }
        });
        // Close on Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') deleteModal.classList.remove('show');
        });
        // AJAX submit
        deleteForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const errorEl = document.getElementById('deleteAccountError');
            const submitBtn = document.getElementById('deleteAccountSubmit');
            const password = document.getElementById('deletePassword').value;

            if (!password) {
                errorEl.textContent = 'Please enter your password.';
                errorEl.classList.add('visible');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
            errorEl.classList.remove('visible');

            fetch(deleteForm.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'password=' + encodeURIComponent(password)
            })
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                if (data.success) {
                    window.location.href = data.redirect || '/';
                } else {
                    errorEl.textContent = data.error || 'Failed to delete account.';
                    errorEl.classList.add('visible');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Delete Account';
                }
            })
            .catch(function () {
                errorEl.textContent = 'Something went wrong. Try again.';
                errorEl.classList.add('visible');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Delete Account';
            });
        });
    }

    // ---------- Hero Slider ----------
    const slides = document.querySelectorAll('.hero-slide');
    const dots = document.querySelectorAll('.hero-dot');
    let currentSlide = 0;
    let slideInterval;

    function showSlide(index) {
        slides.forEach(s => s.classList.remove('active'));
        dots.forEach(d => d.classList.remove('active'));
        if (slides[index]) slides[index].classList.add('active');
        if (dots[index]) dots[index].classList.add('active');
        currentSlide = index;
    }

    function nextSlide() {
        let next = (currentSlide + 1) % slides.length;
        showSlide(next);
    }

    if (slides.length > 0) {
        slideInterval = setInterval(nextSlide, 5000);

        dots.forEach(function (dot, i) {
            dot.addEventListener('click', function () {
                clearInterval(slideInterval);
                showSlide(i);
                slideInterval = setInterval(nextSlide, 5000);
            });
        });
    }

    // ---------- Product Carousel ----------
    document.querySelectorAll('.carousel-section').forEach(function (section) {
        const container = section.querySelector('.carousel-container');
        const prevBtn = section.querySelector('.carousel-prev');
        const nextBtn = section.querySelector('.carousel-next');
        const scrollAmount = 310;

        if (prevBtn && container) {
            prevBtn.addEventListener('click', function () {
                container.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            });
        }

        if (nextBtn && container) {
            nextBtn.addEventListener('click', function () {
                container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            });
        }
    });

    // ---------- Search Modal ----------
    const searchTrigger = document.querySelector('.search-trigger');
    const searchModal = document.querySelector('.search-modal');
    const searchClose = document.querySelector('.search-close');

    if (searchTrigger && searchModal) {
        searchTrigger.addEventListener('click', function () {
            searchModal.classList.add('show');
            const input = searchModal.querySelector('input');
            if (input) input.focus();
        });
    }

    if (searchClose && searchModal) {
        searchClose.addEventListener('click', function () {
            searchModal.classList.remove('show');
        });
    }

    if (searchModal) {
        searchModal.addEventListener('click', function (e) {
            if (e.target === searchModal) {
                searchModal.classList.remove('show');
            }
        });
    }

    // ---------- Category Filter (Products Page) ----------
    const filterTabs = document.querySelectorAll('.filter-tab');
    filterTabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });

    // ---------- Wishlist Heart Toggle ----------
    document.querySelectorAll('.wishlist-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Check if it's a button (interactive) or a link (login redirect)
            if (btn.tagName === 'A') {
                return; // Let the link handle navigation
            }
            
            const productId = btn.getAttribute('data-product-id');
            const isWishlisted = btn.getAttribute('data-wishlisted') === 'true';
            const icon = btn.querySelector('i');
            
            if (!productId) return;
            
            const endpoint = isWishlisted ? '/wishlist/remove' : '/wishlist/add';
            const formData = new FormData();
            formData.append('product_id', productId);
            
            fetch(endpoint, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update button state
                    const newWishlisted = !isWishlisted;
                    btn.setAttribute('data-wishlisted', newWishlisted ? 'true' : 'false');
                    
                    // Update icon
                    if (newWishlisted) {
                        icon.classList.remove('far');
                        icon.classList.add('fas');
                    } else {
                        icon.classList.remove('fas');
                        icon.classList.add('far');
                    }
                    
                    // Show feedback
                    const toast = document.createElement('div');
                    toast.className = 'toast toast-success';
                    toast.textContent = data.message || (newWishlisted ? 'Added to wishlist!' : 'Removed from wishlist!');
                    document.body.appendChild(toast);
                    
                    setTimeout(() => {
                        toast.classList.add('show');
                    }, 10);
                    
                    setTimeout(() => {
                        toast.classList.remove('show');
                        setTimeout(() => toast.remove(), 300);
                    }, 2000);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const toast = document.createElement('div');
                toast.className = 'toast toast-error';
                toast.textContent = 'Error updating wishlist';
                document.body.appendChild(toast);
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => toast.remove(), 300);
                }, 2000);
            });
        });
    });

    // ---------- Smooth Scroll for Anchor Links ----------
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId && targetId !== '#') {
                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });

    // ---------- Fade In on Scroll ----------
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                entry.target.style.opacity = '1';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.product-card, .category-card, .ingredient-card, .testimonial-card').forEach(function (el) {
        el.style.opacity = '0';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // ---------- Main Image Upload Preview ----------
    const mainImageInput = document.querySelector('input[name="image"]');
    if (mainImageInput) {
        mainImageInput.addEventListener('change', function () {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                const preview = document.querySelector('.image-preview');
                reader.onload = function (e) {
                    if (preview) {
                        preview.innerHTML = '<img src="' + e.target.result + '" style="max-width:150px;border-radius:8px;">';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // ---------- Multi-Media Upload Preview ----------
    const mediaInput = document.getElementById('mediaFilesInput');
    const mediaPreviewGrid = document.getElementById('mediaPreviewGrid');
    const mediaUploadArea = document.getElementById('mediaUploadArea');

    if (mediaInput && mediaPreviewGrid) {
        mediaInput.addEventListener('change', function () {
            mediaPreviewGrid.innerHTML = '';
            var files = this.files;
            if (files.length > 0) {
                for (var i = 0; i < files.length; i++) {
                    (function(file, index) {
                        var item = document.createElement('div');
                        item.className = 'media-preview-item';

                        if (file.type.startsWith('video/')) {
                            var video = document.createElement('video');
                            video.src = URL.createObjectURL(file);
                            video.muted = true;
                            video.preload = 'metadata';
                            video.style.cssText = 'width:100%;height:100px;object-fit:cover;border-radius:6px;';
                            item.appendChild(video);
                            var badge = document.createElement('span');
                            badge.className = 'media-type-badge video';
                            badge.innerHTML = '<i class="fas fa-video"></i>';
                            item.appendChild(badge);
                        } else if (file.type.startsWith('image/')) {
                            var reader = new FileReader();
                            reader.onload = function (e) {
                                var img = document.createElement('img');
                                img.src = e.target.result;
                                img.style.cssText = 'width:100%;height:100px;object-fit:cover;border-radius:6px;';
                                item.insertBefore(img, item.firstChild);
                            };
                            reader.readAsDataURL(file);
                            var badge = document.createElement('span');
                            badge.className = 'media-type-badge image';
                            badge.innerHTML = '<i class="fas fa-image"></i>';
                            item.appendChild(badge);
                        }

                        var nameTag = document.createElement('small');
                        nameTag.style.cssText = 'display:block;text-align:center;font-size:0.7rem;color:#888;margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
                        nameTag.textContent = file.name;
                        item.appendChild(nameTag);

                        mediaPreviewGrid.appendChild(item);
                    })(files[i], i);
                }
            }
        });

        // Drag and drop
        if (mediaUploadArea) {
            mediaUploadArea.addEventListener('dragover', function (e) {
                e.preventDefault();
                this.classList.add('drag-over');
            });
            mediaUploadArea.addEventListener('dragleave', function () {
                this.classList.remove('drag-over');
            });
            mediaUploadArea.addEventListener('drop', function (e) {
                e.preventDefault();
                this.classList.remove('drag-over');
                mediaInput.files = e.dataTransfer.files;
                mediaInput.dispatchEvent(new Event('change'));
            });
        }
    }

    // ---------- Confirm Delete ----------
    document.querySelectorAll('.btn-delete').forEach(function (btn) {
        // Skip if the element already has an inline onclick confirm handler
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').indexOf('confirm') !== -1) return;
        btn.addEventListener('click', function (e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // ---------- Form Validation ----------
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            let valid = true;
            const required = form.querySelectorAll('[required]');
            required.forEach(function (field) {
                if (!field.value.trim()) {
                    valid = false;
                    field.style.borderColor = '#e74c3c';
                } else {
                    field.style.borderColor = '';
                }
            });
            if (!valid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });

    // ---------- Dark / Light Mode Toggle ----------
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');

    function setTheme(mode) {
        if (mode === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            if (themeIcon) {
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            }
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            if (themeIcon) {
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            }
            localStorage.setItem('theme', 'light');
        }
    }

    // Apply saved theme on load
    var savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        setTheme('dark');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            setTheme(isDark ? 'light' : 'dark');
        });
    }

    // ---------- Auto-hide Alerts ----------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'all 0.5s ease';
            setTimeout(function () {
                alert.remove();
            }, 500);
        }, 5000);
    });

    // ---------- Password Visibility Toggle ----------
    document.querySelectorAll('.toggle-password').forEach(function (toggle) {
        toggle.addEventListener('click', function () {
            const input = this.previousElementSibling;
            if (input && input.type === 'password') {
                input.type = 'text';
                this.classList.remove('fa-eye');
                this.classList.add('fa-eye-slash');
            } else if (input) {
                input.type = 'password';
                this.classList.remove('fa-eye-slash');
                this.classList.add('fa-eye');
            }
        });
    });

    // ---------- Counter Animation ----------
    function animateCounters() {
        document.querySelectorAll('.stat-number').forEach(function (counter) {
            const target = parseInt(counter.getAttribute('data-count') || counter.textContent);
            if (isNaN(target)) return;
            let current = 0;
            const increment = target / 50;
            const timer = setInterval(function () {
                current += increment;
                if (current >= target) {
                    counter.textContent = target;
                    clearInterval(timer);
                } else {
                    counter.textContent = Math.floor(current);
                }
            }, 30);
        });
    }

    const statsSection = document.querySelector('.dashboard-stats');
    if (statsSection) {
        const statsObserver = new IntersectionObserver(function (entries) {
            if (entries[0].isIntersecting) {
                animateCounters();
                statsObserver.unobserve(statsSection);
            }
        });
        statsObserver.observe(statsSection);
    }

});

// ============================================
// Product Gallery - Switch Media (product detail page)
// ============================================
function switchMedia(thumb, mediaType, src) {
    var container = document.getElementById('galleryMain');
    if (!container) return;

    // Remove active from all thumbs
    document.querySelectorAll('.gallery-thumb').forEach(function(t) {
        t.classList.remove('active');
    });
    thumb.classList.add('active');

    if (mediaType === 'video') {
        container.innerHTML = '<video id="mainMedia" src="' + src + '" controls class="gallery-video" autoplay></video>';
    } else {
        container.innerHTML = '<img id="mainMedia" src="' + src + '" alt="Product">';
    }
}

document.addEventListener('click', function(e) {
    var thumb = e.target.closest('.gallery-thumb');
    if (!thumb) return;

    var mediaType = thumb.getAttribute('data-media-type');
    var mediaSrc = thumb.getAttribute('data-media-src');
    if (!mediaType || !mediaSrc) return;

    e.preventDefault();
    switchMedia(thumb, mediaType, mediaSrc);
});

// ============================================
// Remove Existing Media (admin manage products)
// ============================================
function removeExistingMedia(mediaId, btn) {
    if (!confirm('Remove this media file?')) return;
    var item = document.getElementById('media-item-' + mediaId);

    fetch('/admin/products?delete_media=' + mediaId, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
        if (data.success && item) {
            item.style.transition = 'opacity 0.3s, transform 0.3s';
            item.style.opacity = '0';
            item.style.transform = 'scale(0.8)';
            setTimeout(function() { item.remove(); }, 300);
        }
    })
    .catch(function() {
        alert('Failed to remove media. Please try again.');
    });
}


// ============================================
// Cart Functionality
// ============================================

// ---------- Add to Cart (AJAX) ----------
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.add-to-cart-btn');
    if (!btn) return;
    e.preventDefault();

    var productId = btn.getAttribute('data-product-id');
    if (!productId) return;

    btn.disabled = true;
    var origHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    var formData = new FormData();
    formData.append('product_id', productId);
    formData.append('quantity', 1);

    fetch('/cart/add', {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
        if (data.success) {
            // Update cart badge
            updateCartBadge(data.cart_count);
            // Show toast
            showCartToast(data.message);
            btn.innerHTML = '<i class="fas fa-check"></i> Added';
            setTimeout(function() {
                btn.innerHTML = origHTML;
                btn.disabled = false;
            }, 1500);
        } else {
            // Not logged in or error
            if (data.message && data.message.toLowerCase().includes('login')) {
                window.location.href = '/login';
            } else {
                alert(data.message || 'Failed to add to cart.');
                btn.innerHTML = origHTML;
                btn.disabled = false;
            }
        }
    })
    .catch(function() {
        // If not logged in, the response won't be JSON - redirect to login
        window.location.href = '/login';
    });
});

// ---------- Update Cart Badge ----------
function updateCartBadge(count) {
    var badge = document.getElementById('cartBadge');
    var cartLink = document.querySelector('.nav-cart-link');
    if (count > 0) {
        if (badge) {
            badge.textContent = count;
        } else if (cartLink) {
            var span = document.createElement('span');
            span.className = 'cart-badge';
            span.id = 'cartBadge';
            span.textContent = count;
            cartLink.appendChild(span);
        }
    } else if (badge) {
        badge.remove();
    }
}

// ---------- Show Toast Notification ----------
function showCartToast(message) {
    // Remove existing toast
    var existing = document.querySelector('.cart-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.className = 'cart-toast';
    toast.innerHTML = '<i class="fas fa-check-circle"></i> ' + message;
    document.body.appendChild(toast);

    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(function() { toast.remove(); }, 300);
    }, 2500);
}

// ---------- Update Cart Quantity (AJAX) ----------
function updateCartQty(cartId, newQty) {
    if (newQty < 0) return;

    var formData = new FormData();
    formData.append('cart_id', cartId);
    formData.append('quantity', newQty);

    fetch('/cart/update', {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
        if (data.success) {
            if (newQty <= 0) {
                // Remove item from DOM
                var item = document.getElementById('cartItem' + cartId);
                if (item) {
                    item.style.transition = 'opacity 0.3s, transform 0.3s';
                    item.style.opacity = '0';
                    item.style.transform = 'translateX(-20px)';
                    setTimeout(function() { item.remove(); checkEmptyCart(); }, 300);
                }
            } else {
                // Reload page to update all calculated values
                window.location.reload();
            }
            updateCartBadge(data.cart_count);
        }
    })
    .catch(function() {
        window.location.reload();
    });
}

function checkEmptyCart() {
    var items = document.querySelectorAll('.cart-item');
    if (items.length === 0) {
        window.location.reload();
    }
}