// /my_career_portal/static/js/main.js
// Example: Smooth scroll for anchor links (like on the home page "Explore Tools")
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        if (targetId === "#") return; // Ignore href="#"
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

console.log("Main JS loaded.");