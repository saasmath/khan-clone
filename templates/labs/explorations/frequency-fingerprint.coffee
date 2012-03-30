$(->
    # Draw Chart
    chartOptions = {
        chart: {
            renderTo: 'chart'
            type:     'column'
        }

        colors: ['#3366cc']

        credits: {
            enabled: no
        }

        legend: {
            enabled: no
        }

        series: [
            {
                data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            }
        ]

        title: {
            text: ''
        }

        tooltip: {
            formatter: ->
                return @x + ': ' + @y
        }

        xAxis: {
            categories: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        }

        yAxis: {
            allowDecimals: no

            title: {
                text: ''
            }
        }
    }

    window.chart = new Highcharts.Chart(chartOptions)

    $('textarea').on('keyup', (event) ->
        # Update Chart
        data = []

        for letter in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
            match = @value.match(new RegExp(letter, 'gi'))

            if match
                letterCount = match.length
            else
                letterCount = 0

            data.push(letterCount)

        maxLetterCount = Math.max.apply(Math, data)

        while data.indexOf(maxLetterCount) isnt -1
            data[data.indexOf(maxLetterCount)] = {color: '#dc3912', y: maxLetterCount}

        window.chart.series[0].setData(data)
    )
)
