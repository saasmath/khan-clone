(function() {
  var LETTERS, shifts;

  LETTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'];

  shifts = [];

  $(function() {
    var char, chart1, chart1Options, chart2, chart2Options, chart3, chart3Options, defaultOptions, i, letter, timeout, updateCharts;
    defaultOptions = {
      chart: {
        animation: false,
        type: 'column'
      },
      colors: ['#3366cc'],
      credits: {
        enabled: false
      },
      legend: {
        enabled: false
      },
      series: [
        {
          data: (function() {
            var _i, _len, _results;
            _results = [];
            for (_i = 0, _len = LETTERS.length; _i < _len; _i++) {
              letter = LETTERS[_i];
              _results.push(0);
            }
            return _results;
          })()
        }
      ],
      title: {
        text: ''
      },
      tooltip: {
        formatter: function() {
          return this.x + ': ' + this.y;
        }
      },
      xAxis: {
        labels: {
          staggerLines: 2
        }
      },
      yAxis: {
        allowDecimals: false,
        title: {
          text: ''
        }
      }
    };
    chart1Options = $.extend(true, {}, defaultOptions, {
      chart: {
        renderTo: 'chart1'
      },
      xAxis: {
        categories: (function() {
          var _i, _len, _results;
          _results = [];
          for (_i = 0, _len = LETTERS.length; _i < _len; _i++) {
            letter = LETTERS[_i];
            _results.push(letter.toUpperCase());
          }
          return _results;
        })()
      }
    });
    chart1 = new Highcharts.Chart(chart1Options);
    chart2Options = $.extend(true, {}, defaultOptions, {
      chart: {
        renderTo: 'chart2'
      },
      xAxis: {
        categories: (function() {
          var _len, _results;
          _results = [];
          for (i = 0, _len = LETTERS.length; i < _len; i++) {
            char = LETTERS[i];
            _results.push(i + 1);
          }
          return _results;
        })()
      }
    });
    chart2 = new Highcharts.Chart(chart2Options);
    chart3Options = $.extend(true, {}, defaultOptions, {
      chart: {
        renderTo: 'chart3'
      },
      xAxis: {
        categories: (function() {
          var _i, _len, _results;
          _results = [];
          for (_i = 0, _len = LETTERS.length; _i < _len; _i++) {
            letter = LETTERS[_i];
            _results.push(letter.toUpperCase());
          }
          return _results;
        })()
      }
    });
    chart3 = new Highcharts.Chart(chart3Options);
    updateCharts = function(value) {
      var char, chars, ciphertext, ciphertextChar, ciphertextLetterCount, ciphertextLetterIndex, html, i, letter, letterIndex, max, plaintext, plaintextChar, plaintextLetterCount, randomShiftChar, randomShifts, shift, shiftCount, shiftIndex, _i, _len, _len2;
      if (value === '') value = ' ';
      ciphertext = '';
      ciphertextLetterCount = (function() {
        var _i, _len, _results;
        _results = [];
        for (_i = 0, _len = LETTERS.length; _i < _len; _i++) {
          letter = LETTERS[_i];
          _results.push(0);
        }
        return _results;
      })();
      plaintext = '';
      plaintextLetterCount = (function() {
        var _i, _len, _results;
        _results = [];
        for (_i = 0, _len = LETTERS.length; _i < _len; _i++) {
          letter = LETTERS[_i];
          _results.push(0);
        }
        return _results;
      })();
      randomShifts = [];
      shiftCount = (function() {
        var _i, _len, _results;
        _results = [];
        for (_i = 0, _len = LETTERS.length; _i < _len; _i++) {
          letter = LETTERS[_i];
          _results.push(0);
        }
        return _results;
      })();
      shiftIndex = 0;
      for (_i = 0, _len = value.length; _i < _len; _i++) {
        char = value[_i];
        letterIndex = LETTERS.indexOf(char.toLowerCase());
        plaintext += char;
        if (letterIndex === -1) {
          ciphertext += char;
          randomShifts.push(' ');
        } else {
          while (shifts.length - shiftIndex < 1) {
            shifts.push(Math.floor(Math.random() * 26) + 1);
          }
          shift = shifts[shiftIndex];
          ciphertextLetterIndex = (letterIndex + shift) % 26;
          ciphertext += LETTERS[ciphertextLetterIndex];
          ciphertextLetterCount[ciphertextLetterIndex] += 1;
          plaintextLetterCount[letterIndex] += 1;
          randomShifts.push(shift);
          shiftCount[shift - 1] += 1;
          shiftIndex += 1;
        }
      }
      ciphertext = ciphertext.toUpperCase();
      while (shifts.length > shiftIndex) {
        shifts.pop();
      }
      html = '<div id="chars">';
      for (i = 0, _len2 = plaintext.length; i < _len2; i++) {
        char = plaintext[i];
        if (char === ' ') {
          ciphertextChar = '&nbsp;';
          plaintextChar = '&nbsp;';
          randomShiftChar = '&nbsp;';
        } else {
          ciphertextChar = ciphertext[i];
          plaintextChar = char;
          randomShiftChar = randomShifts[i];
        }
        html += "<div class=\"char\">\n    " + plaintextChar + "\n    <br>\n    " + randomShiftChar + "\n    <br>\n    " + ciphertextChar + "\n</div>";
      }
      html += '</div>';
      $('#chars').replaceWith(html);
      chars = $('#chars');
      chars.scrollLeft(chars[0].scrollWidth);
      max = Math.max.apply(Math, ciphertextLetterCount.concat(plaintextLetterCount, shiftCount));
      chart1.yAxis[0].setExtremes(0, max);
      chart1.series[0].setData(plaintextLetterCount);
      chart2.yAxis[0].setExtremes(0, max);
      chart2.series[0].setData(shiftCount);
      chart3.yAxis[0].setExtremes(0, max);
      return chart3.series[0].setData(ciphertextLetterCount);
    };
    timeout = null;
    return $('textarea').on('keyup', function() {
      var _this = this;
      clearTimeout(timeout);
      return timeout = setTimeout(function() {
        return updateCharts(_this.value);
      }, 150);
    });
  });

}).call(this);
