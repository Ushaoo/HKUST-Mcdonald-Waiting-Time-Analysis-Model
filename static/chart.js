// 加载历史数据并渲染图表
fetch('/api/history')
  .then(res => res.json())
  .then(data => {
    renderWeeklyFlow(data.weekly_flow);
    renderPeakTimes(data.peak_times);
    renderHeatmap(data.heatmap);
  })
  .catch(err => console.error('加载数据失败:', err));

function renderWeeklyFlow(values) {
  new Chart(document.getElementById('weeklyFlowChart'), {
    type: 'line',
    data: {
      labels: ['周一','周二','周三','周四','周五','周六','周日'],
      datasets: [{
        label: '人流量',
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
        label: '高峰人数',
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
        label: `周${['一','二','三'][i]}`,
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
