// Animation des images et interactions

document.addEventListener('DOMContentLoaded', function() {
    
    // === MENU CHAPITRES ===
    // Gérer l'ouverture/fermeture du menu des chapitres
    const chaptersToggle = document.querySelector('.chapters-toggle');
    const chaptersMenu = document.querySelector('.chapters-menu');
    
    if (chaptersToggle && chaptersMenu) {
        chaptersToggle.addEventListener('click', function(e) {
            e.preventDefault();
            // Basculer la classe 'show' pour afficher/masquer le menu
            chaptersMenu.classList.toggle('show');
        });
        
        // Fermer le menu quand on clique sur un lien de chapitre
        const chapterLinks = chaptersMenu.querySelectorAll('a');
        chapterLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                chaptersMenu.classList.remove('show');
            });
        });
    }
    
    // === BOUTON RETOUR EN HAUT ===
    // Créer et gérer le bouton de retour en haut
    const backToTopBtn = document.querySelector('.back-to-top');
    
    if (backToTopBtn) {
        // Afficher le bouton quand on descend dans la page
        window.addEventListener('scroll', function() {
            if (window.scrollY > 300) {
                backToTopBtn.classList.add('show');
            } else {
                backToTopBtn.classList.remove('show');
            }
        });
        
        // Remonter en haut au clic
        backToTopBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.scrollTo({
                top: 0,
                behavior: 'smooth' // Animation fluide
            });
        });
    }
    
    // === ANIMATION DES CARTES DE CHAPITRES ===
    // Animer les cartes quand elles apparaissent à l'écran
    const chapterCards = document.querySelectorAll('.chapter-card');
    
    // Observer pour détecter quand les éléments entrent dans la vue
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                // Ajouter la classe d'animation
                entry.target.classList.add('animate-on-scroll');
                // Arrêter d'observer cet élément
                observer.unobserve(entry.target);
            }
        });
    });
    
    // Observer toutes les cartes de chapitres
    chapterCards.forEach(function(card) {
        observer.observe(card);
    });
    
    // === ANIMATION AU SURVOL DES IMAGES ===
    // Effet de zoom sur les images des chapitres
    chapterCards.forEach(function(card) {
        const img = card.querySelector('img');
        
        if (img) {
            // Au survol : légère rotation et zoom
            card.addEventListener('mouseenter', function() {
                img.style.transform = 'scale(1.1) rotate(2deg)';
                img.style.transition = 'transform 0.3s ease';
            });
            
            // Quand on quitte : retour normal
            card.addEventListener('mouseleave', function() {
                img.style.transform = 'scale(1) rotate(0deg)';
            });
        }
    });
    
    // === ANIMATION DES LIENS DE NAVIGATION ===
    // Effet sur les liens de navigation
    const navLinks = document.querySelectorAll('.nav-links a');
    
    navLinks.forEach(function(link) {
        link.addEventListener('mouseenter', function() {
            // Effet de soulignement animé
            this.style.borderBottom = '2px solid var(--primary-color)';
            this.style.transition = 'border-bottom 0.3s ease';
        });
        
        link.addEventListener('mouseleave', function() {
            this.style.borderBottom = 'none';
        });
    });
    
    // === ANIMATION DE LA PHOTO DE L'ENSEIGNANT ===
    const teacherPhoto = document.querySelector('.teacher-photo');
    
    if (teacherPhoto) {
        teacherPhoto.addEventListener('mouseenter', function() {
            // Effet de rotation et ombre
            this.style.transform = 'rotate(5deg) scale(1.1)';
            this.style.boxShadow = '0 10px 20px rgba(0,0,0,0.2)';
            this.style.transition = 'all 0.3s ease';
        });
        
        teacherPhoto.addEventListener('mouseleave', function() {
            this.style.transform = 'rotate(0deg) scale(1)';
            this.style.boxShadow = 'none';
        });
    }
    
    // === ANIMATION DES BOUTONS ===
    const buttons = document.querySelectorAll('.btn');
    
    buttons.forEach(function(btn) {
        btn.addEventListener('mouseenter', function() {
            // Effet de pulsation
            this.style.transform = 'scale(1.05)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
        
        // Effet au clic
        btn.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'scale(1.05)';
            }, 100);
        });
    });
    
    // === ANIMATION DU LOGO ===
    const logo = document.querySelector('.logo h1');
    
    if (logo) {
        logo.addEventListener('mouseenter', function() {
            // Animation de couleur
            this.style.color = 'var(--primary-color)';
            this.style.transition = 'color 0.3s ease';
        });
        
        logo.addEventListener('mouseleave', function() {
            this.style.color = '';
        });
    }
    
    // === PARALLAX SIMPLE POUR LE HEADER ===
    const pageHeader = document.querySelector('.page-header');
    
    if (pageHeader) {
        window.addEventListener('scroll', function() {
            const scrolled = window.scrollY;
            const rate = scrolled * -0.5; // Vitesse du parallax
            
            pageHeader.style.backgroundPosition = `center ${rate}px`;
        });
    }
    
});
