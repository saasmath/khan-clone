function KOFastFilter(params) {
    this.elementList = [];
    this.params = params || {};

    this.addElement = function(element, viewModel) {
        this.elementList.push({'element':element, 'viewModel':viewModel});
    };

    this.doFilter = function(root_element, filter_function) {
        // Detach root element to speed up DOM operations
        var root = null, nextElement = null, parentElement = null;
        var self = this;

        if (root_element)
            root = $(root_element);

        if (root) {
            nextElement = root.next();
            if (nextElement.length == 0)
                parentElement = root.parent();
            root.detach();
        }

        // Update visibility of each element based on result of callback function
        $.each(this.elementList, function(idx, row) {
            var visible = filter_function(row.viewModel);
            if ('css' in self.params) {
                if (visible)
                    $(row.element).addClass(params.css);
                else
                    $(row.element).removeClass(params.css);
            } else {
                if (visible)
                    $(row.element).show();
                else
                    $(row.element).hide();
            }
        });

        // Reattach root element
        if (root) {
            if (nextElement.length > 0)
                root.insertBefore(nextElement);
            else
                root.appendTo(parentElement);
        }
    };
}

$(function() {
    ko.bindingHandlers['fastFilter'] = {
        'init': function(element, valueAccessor, allBindingsAccessor, viewModel) {
            var filter = valueAccessor();
            if (filter instanceof KOFastFilter) {
                filter.addElement(element, viewModel);
            } else {
                throw new Error('Attempting to use a fastFilter KO binding with a paramter that is not a KOFastFilter object.');
            }
        },
    };
});

// Executes the default template N times with properties 'index' (0..N-1) and 'total' (N) on the data.
ko.bindingHandlers['countToN'] = {
    makeTemplateValueAccessor: function(valueAccessor) {
        return function() { 
            var bindingValue = ko.utils.unwrapObservable(valueAccessor());
            var arrayValue = [];
            for (var idx = 0; idx < bindingValue*1; idx++)
                arrayValue.push({'index':idx,'total':bindingValue*1});
            
            return { 'foreach': arrayValue, 'templateEngine': ko.nativeTemplateEngine.instance };
        };
    },
    'init': function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {		
        return ko.bindingHandlers['template']['init'](element, ko.bindingHandlers['countToN'].makeTemplateValueAccessor(valueAccessor));
    },
    'update': function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
        return ko.bindingHandlers['template']['update'](element, ko.bindingHandlers['countToN'].makeTemplateValueAccessor(valueAccessor), allBindingsAccessor, viewModel, bindingContext);
    }
};

function KOStyleSwitch(possible_types, defaultType, variable) {
    var self = this;
    $.each(possible_types, function(idx, type) {
        self['is'+type] = ko.dependentObservable(function() { return ko.utils.unwrapObservable(this) == type; }, variable);
    });
    self['is'+defaultType] = ko.dependentObservable(function() {
        var currentType = ko.utils.unwrapObservable(this);
        var ret = true;
        $.each(possible_types, function(idx, type) {
            if (currentType == type) { ret = false; return false; }
        });
        return ret;
    }, variable);
}

//wrapper for a dependentObservable that can pause its subscriptions 

var KOBulkUpdate = {
    isPaused: ko.observable(false),
    updateList: [],

    //keep track of our current values and set the pause flag to release our actual subscriptions
    pause: function() {
        $.each(KOBulkUpdate.updateList, function(idx, observable) {
            observable._cachedValue = observable();
        });
        KOBulkUpdate.isPaused(true);
    },

    //clear the cached values and allow our dependentObservable to be re-evaluated
    resume: function() {
        $.each(KOBulkUpdate.updateList, function(idx, observable) {
            observable._cachedValue = "";
        });
        KOBulkUpdate.isPaused(false);
    },

    dependentObservable: function(evaluatorFunction, evaluatorFunctionTarget) {
        var _cachedValue = "";  

        var result = ko.dependentObservable(function() {
            if (!KOBulkUpdate.isPaused()) {
                //call the actual function that was passed in
                return evaluatorFunction.call(evaluatorFunctionTarget);
            }

            return _cachedValue;
        }, evaluatorFunctionTarget);

        return result;
    },
};

