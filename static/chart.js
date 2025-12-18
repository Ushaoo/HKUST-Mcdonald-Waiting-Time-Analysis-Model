// Load historical data and render charts
fetch('/api/history')
  .then(res => res.json())
  .then(data => {
    renderWeeklyFlow(data.weekly_flow);
    renderPeakTimes(data.peak_times);
    renderHeatmap(data.heatmap);
  })
  .catch(err => console.error('Failed to load data:', err));

function renderWeeklyFlow(values) {
  new Chart(document.getElementById('weeklyFlowChart'), {
    type: 'line',
    data: {
      labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
      datasets: [{
        label: 'Crowd Flow',
        data: values,
        borderColor: '#FFC72C',
        backgroundColor: 'rgba(255,199,44,0.2)',
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: '#C8A951'
          }
        }
      },
      scales: {
        y: {
          ticks: {
            color: '#C8A951'
          },
          grid: {
            color: 'rgba(200, 169, 81, 0.1)'
          }
        },
        x: {
          ticks: {
            color: '#C8A951'
          },
          grid: {
            color: 'rgba(200, 169, 81, 0.1)'
          }
        }
      }
    }
  });
}

function renderPeakTimes(times) {
  new Chart(document.getElementById('peakTimeChart'), {
    type: 'bar',
    data: {
      labels: Object.keys(times),
      datasets: [{
        label: 'Peak People Count',
        data: Object.values(times),
        backgroundColor: '#DA291C'
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: '#C8A951'
          }
        }
      },
      scales: {
        y: {
          ticks: {
            color: '#C8A951'
          },
          grid: {
            color: 'rgba(200, 169, 81, 0.1)'
          }
        },
        x: {
          ticks: {
            color: '#C8A951'
          },
          grid: {
            color: 'rgba(200, 169, 81, 0.1)'
          }
        }
      }
    }
  });
}

function renderHeatmap(matrix) {
  const ctx = document.getElementById('heatmapChart').getContext('2d');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['10:00','14:00','18:00','22:00'],
      datasets: matrix.map((row, i) => ({
        label: `Day ${['1','2','3'][i]}`,
        data: row,
        backgroundColor: ['#FFF2B0','#FFD85C','#FFC72C','#DA291C']
      }))
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: '#C8A951'
          }
        }
      },
      scales: {
        y: {
          ticks: {
            color: '#C8A951'
          },
          grid: {
            color: 'rgba(200, 169, 81, 0.1)'
          }
        },
        x: {
          ticks: {
            color: '#C8A951'
          },
          grid: {
            color: 'rgba(200, 169, 81, 0.1)'
          }
        }
      }
    }
  });
}
