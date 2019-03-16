// Copyright 2018 AstroLab Software
// Author: Julien Peloton
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// This function serves the Fink documentation.
// Please change the csvURL if data does not display (hardcoded...)
function createChart() {
    Highcharts.chart('container_live', {
        chart: {
            type: 'spline',
            zoomType: 'x'
        },
        title: {
            text: 'Live Data Simulator'
        },
        yAxis: {
          title: {
            text: 'Rate'
          }
        },
        data: {
            csvURL: window.location.origin + '../data/live.csv',
            enablePolling: true,
            dataRefreshRate: 1
        }
    });

    if (pollingInput.value < 1 || !pollingInput.value) {
        pollingInput.value = 1;
    }
}

// Create the chart
createChart();
