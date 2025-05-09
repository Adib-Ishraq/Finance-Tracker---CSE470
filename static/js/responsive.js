// Mobile detection and responsive helpers
const FinanceApp = {
    // Check if device is mobile
    isMobile: function() {
        return window.innerWidth < 768;
    },
    
    // Apply mobile-specific adjustments
    applyMobileStyles: function() {
        if (this.isMobile()) {
            // Add mobile-specific classes to elements
            document.querySelectorAll('.desktop-optimized').forEach(el => {
                el.classList.add('mobile-optimized');
            });
            
            // Adjust chart options for better mobile display
            if (typeof Chart !== 'undefined') {
                Chart.defaults.font.size = 10;
                Chart.defaults.plugins.legend.position = 'bottom';
            }
        } else {
            // Reset to desktop styles
            document.querySelectorAll('.mobile-optimized').forEach(el => {
                el.classList.remove('mobile-optimized');
            });
            
            // Reset chart options for desktop
            if (typeof Chart !== 'undefined') {
                Chart.defaults.font.size = 12;
                Chart.defaults.plugins.legend.position = 'right';
            }
        }
    },
    
    // Initialize responsive behaviors
    initResponsive: function() {
        // Apply initial styles
        this.applyMobileStyles();
        
        // Listen for window resize
        window.addEventListener('resize', () => {
            this.applyMobileStyles();
        });
        
        // Make tables responsive
        this.makeTablesResponsive();
    },
    
    // Make tables responsive
    makeTablesResponsive: function() {
        const tables = document.querySelectorAll('.table-responsive-custom');
        
        tables.forEach(table => {
            const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
            
            table.querySelectorAll('tbody tr').forEach(row => {
                Array.from(row.querySelectorAll('td')).forEach((cell, index) => {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        });
    }
};

// Initialize responsive behaviors when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    FinanceApp.initResponsive();
});
