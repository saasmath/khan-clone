/* ============================================================
 * bootstrap-dropdown.js v2.0.1
 * http://twitter.github.com/bootstrap/javascript.html#dropdowns
 * ============================================================
 * Copyright 2012 Twitter, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ============================================================ */


!function( $ ){

  "use strict"

 /* DROPDOWN CLASS DEFINITION
  * ========================= */

  var toggle = '[data-toggle="dropdown"]'
    , Dropdown = function ( element, option ) {
        if (option === 'hover') {
            $(element).hoverIntent(
                function () {
                    $(this).dropdown('open')
                },
                $.noop
            ).parent().hoverIntent(
                $.noop,
                function () {
                    $(this).find('.dropdown-toggle').dropdown('close')
                }
            );
        } else {
            $(element).on('click.dropdown.data-api', this.toggle)
        }
      }

  Dropdown.prototype = {

    constructor: Dropdown

  , toggle: function ( e ) {
      var $this = $(this)
        , selector = $this.attr('data-target')
        , $parent
        , isActive

      if (!selector) {
        selector = $this.attr('href')
        selector = selector && selector.replace(/.*(?=#[^\s]*$)/, '') //strip for ie7
      }

      $parent = $(selector)
      $parent.length || ($parent = $this.parent())

      isActive = $parent.hasClass('open')

      if (isActive) {
        Dropdown.prototype.close.call(this)
      } else {
        Dropdown.prototype.open.call(this)
      }

      return false
    }
  , open: function () {
      $(this).trigger('open')
        .parent().addClass('open')
    }
  , close: function () {
      clearMenus()
    }
  }

  function clearMenus() {
    $(toggle).trigger('close')
        .parent().removeClass('open')
  }


  /* DROPDOWN PLUGIN DEFINITION
   * ========================== */

  $.fn.dropdown = function ( option ) {
    return this.each(function () {
      var $this = $(this)
        , data = $this.data('dropdown')
      if (!data) {
          $this.data('dropdown', (data = new Dropdown(this, option)))
      }
      if (typeof option == 'string') {
          var action = data[option]
          if (action) {
              action.call(this)
          }
      }
    })
  }

  $.fn.dropdown.Constructor = Dropdown


  /* APPLY TO STANDARD DROPDOWN ELEMENTS
   * =================================== */

  $(function () {
    $('html').on('click.dropdown.data-api', clearMenus)
  })

}( window.jQuery );
