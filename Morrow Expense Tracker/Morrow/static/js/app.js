document.addEventListener('DOMContentLoaded', () => {
  const dialog = document.querySelector('#expenseDialog');
  document.querySelectorAll('[data-open-expense]').forEach((button) => {
    button.addEventListener('click', () => dialog?.showModal());
  });
  dialog?.querySelector('.dialog-close button')?.addEventListener('click', (event) => {
    event.preventDefault();
    dialog.close();
  });
  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });

  const payload = document.querySelector('#dashboard-data');
  if (!payload || !window.Chart) return;
  const data = JSON.parse(payload.textContent);
  const colors = ['#167c78', '#e58e68', '#718cdd', '#d5ac45', '#d97883', '#63a6bb', '#a576ad', '#8a9a88'];
  Chart.defaults.font.family = 'DM Sans, sans-serif';
  Chart.defaults.color = '#969992';

  const categoryCanvas = document.querySelector('#categoryChart');
  if (categoryCanvas && data.categories.length) {
    new Chart(categoryCanvas, {
      type: 'doughnut',
      data: { labels: data.categories, datasets: [{ data: data.amounts, backgroundColor: data.categories.map((_, i) => colors[i % colors.length]), borderWidth: 0, hoverOffset: 5, spacing: 3, borderRadius: 5 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '77%', plugins: { legend: { display: false }, tooltip: { backgroundColor: '#25322b', padding: 11, cornerRadius: 9, callbacks: { label: (context) => ` $${context.parsed.toLocaleString('en-US', { minimumFractionDigits: 2 })}` } } } }
    });
  }

  const dailyCanvas = document.querySelector('#dailyChart');
  if (dailyCanvas) {
    const labels = Object.keys(data.daily).sort();
    const values = labels.map((day) => data.daily[day]);
    const gradient = dailyCanvas.getContext('2d').createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, 'rgba(22, 124, 120, .24)');
    gradient.addColorStop(1, 'rgba(22, 124, 120, 0)');
    new Chart(dailyCanvas, {
      type: 'line',
      data: { labels, datasets: [{ data: values, borderColor: '#167c78', backgroundColor: gradient, fill: true, tension: .38, borderWidth: 3, pointRadius: 4, pointHoverRadius: 7, pointBackgroundColor: '#fff', pointBorderColor: '#167c78', pointBorderWidth: 2 }] },
      options: { responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: 'index' }, plugins: { legend: { display: false }, tooltip: { backgroundColor: '#25322b', padding: 11, cornerRadius: 9, displayColors: false, callbacks: { title: (items) => new Date(`${items[0].label}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), label: (item) => ` $${item.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2 })}` } } }, scales: { x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 7, maxRotation: 0, callback: function(value) { const day = new Date(`${this.getLabelForValue(value)}T00:00:00`); return day.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); } } }, y: { beginAtZero: true, grid: { color: '#f0f1ed', drawTicks: false }, border: { display: false }, ticks: { padding: 10, maxTicksLimit: 5, callback: (value) => `$${value}` } } } }
    });
  }

  document.querySelectorAll('.toast').forEach((toast, index) => {
    window.setTimeout(() => toast.classList.add('toast-out'), 3400 + index * 200);
    window.setTimeout(() => toast.remove(), 3900 + index * 200);
  });
});
