$(->
    defaultOptions = {
        chart: {
            type: 'column'
        }

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

        credits: {
            enabled: no
        }

        legend: {
            align:         'right'
            borderWidth:   0
            layout:        'vertical'
            verticalAlign: 'top'
        }

        title: {
            text: ''
        }

        tooltip: {
            formatter: ->
                return @series.name + ': ' + @y
        }

        xAxis: {
            categories: ['']
        }

        yAxis: {
            allowDecimals: no

            title: {
                text: ''
            }
        }
    }

    # Draw Chart 1
    chart1Options = {}

    $.extend(yes, chart1Options, defaultOptions, {
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
    chart2Options = {}

    $.extend(yes, chart2Options, defaultOptions, {
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
    chart3Options = {}

    $.extend(yes, chart3Options, defaultOptions, {
        chart: {
            renderTo: 'chart3'
        }

        series: [
            {data: [0], name: '000'}
            {data: [0], name: '100'}
            {data: [0], name: '010'}
            {data: [0], name: '001'}
            {data: [0], name: '110'}
            {data: [0], name: '101'}
            {data: [0], name: '011'}
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
        ones   = @value.match(/1/g)?.length or 0
        zeroes = @value.match(/0/g)?.length or 0

        window.chart1.series[0].setData([zeroes], no)
        window.chart1.series[1].setData([ones])

        # Update Chart 2
        zeroZeroes = @value.match(/0(?=0)/g)?.length or 0
        zeroOnes   = @value.match(/0(?=1)/g)?.length or 0
        oneZeroes  = @value.match(/1(?=0)/g)?.length or 0
        oneOnes    = @value.match(/1(?=1)/g)?.length or 0

        window.chart2.series[0].setData([zeroZeroes], no)
        window.chart2.series[1].setData([zeroOnes], no)
        window.chart2.series[2].setData([oneZeroes], no)
        window.chart2.series[3].setData([oneOnes])

        # Update Chart 3
        zeroZeroZeroes = @value.match(/0(?=00)/g)?.length or 0
        oneZeroZeroes  = @value.match(/1(?=00)/g)?.length or 0
        zeroOneZeroes  = @value.match(/0(?=10)/g)?.length or 0
        zeroZeroOnes   = @value.match(/0(?=01)/g)?.length or 0
        oneOneZeroes   = @value.match(/1(?=10)/g)?.length or 0
        oneZeroOnes    = @value.match(/1(?=01)/g)?.length or 0
        zeroOneOnes    = @value.match(/0(?=11)/g)?.length or 0
        oneOneOnes     = @value.match(/1(?=11)/g)?.length or 0

        window.chart3.series[0].setData([zeroZeroZeroes], no)
        window.chart3.series[1].setData([oneZeroZeroes], no)
        window.chart3.series[2].setData([zeroOneZeroes], no)
        window.chart3.series[3].setData([zeroZeroOnes], no)
        window.chart3.series[4].setData([oneOneZeroes], no)
        window.chart3.series[5].setData([oneZeroOnes], no)
        window.chart3.series[6].setData([zeroOneOnes], no)
        window.chart3.series[7].setData([oneOneOnes])
    )
)
