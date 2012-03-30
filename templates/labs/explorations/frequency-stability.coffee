$ ->
    defaultOptions =
        chart:
            type: 'column'
        colors: [
            '#3366cc'
            '#dc3912'
            '#ff9900'
            '#109618'
            '#990099'
            '#0099c6'
            '#dd4477'
            '#66aa00'
        ]
        credits:
            enabled: no
        legend:
            align:         'right'
            borderWidth:   0
            layout:        'vertical'
            verticalAlign: 'top'
        title:
            text: ''
        tooltip:
            formatter: -> @series.name + ': ' + @y
        xAxis:
            categories: ['']
        yAxis:
            allowDecimals: no
            title:
                text: ''

    # Draw Chart 1
    chart1Options = $.extend(yes, {}, defaultOptions, {
        chart: {
            renderTo: 'chart1'
        }

        series: [
            {data: [0], name: '0'}
            {data: [0], name: '1'}
        ]
    })

    window.chart1 = new Highcharts.Chart(chart1Options)

    # Draw Chart 2
    chart2Options = $.extend(yes, {}, defaultOptions, {
        chart: {
            renderTo: 'chart2'
        }

        series: [
            {data: [0], name: '00'}
            {data: [0], name: '01'}
            {data: [0], name: '10'}
            {data: [0], name: '11'}
        ]
    })

    window.chart2 = new Highcharts.Chart(chart2Options)

    # Draw Chart 3
    chart3Options = $.extend(yes, {}, defaultOptions, {
        chart: {
            renderTo: 'chart3'
        }

        series: [
            {data: [0], name: '000'}
            {data: [0], name: '001'}
            {data: [0], name: '010'}
            {data: [0], name: '011'}
            {data: [0], name: '100'}
            {data: [0], name: '101'}
            {data: [0], name: '110'}
            {data: [0], name: '111'}
        ]
    })

    window.chart3 = new Highcharts.Chart(chart3Options)

    $('.btn').on('click', ->
        btn = $(@)

        if btn.is('#random')
            range = [1..1000]
        else
            range = []

        numbers = ''
        numbers += Math.round(Math.random()) for i in range

        input = $('input')
        input.val(numbers)
        input.trigger('keyup')
    )

    $('input').on('keyup', (event) ->
        # Update Chart 1
        onegexes = [/0/g, /1/g]
        for i in [0..1]
            count = @value.match(onegexes[i])?.length or 0
            window.chart1.series[i].setData([count], i == 1)

        # Update Chart 2
        twogexes = [/0(?=0)/g, /0(?=1)/g, /1(?=0)/g, /1(?=1)/g]
        for i in [0..3]
            count = @value.match(twogexes[i])?.length or 0
            window.chart2.series[i].setData([count], i == 3)

        # Update Chart 3
        threegexes = [
            /0(?=00)/g, /0(?=01)/g, /0(?=10)/g, /0(?=11)/g
            /1(?=00)/g, /1(?=01)/g, /1(?=10)/g, /1(?=11)/g
        ]
        for i in [0..7]
            count = @value.match(threegexes[i])?.length or 0
            window.chart3.series[i].setData([count], i == 7)
    )
