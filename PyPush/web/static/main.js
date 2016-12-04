'use strict';

angular.module("PyPushApp", ["ngResource", 'ui.bootstrap', 'ui.bootstrap.tpls', 'xeditable'])
	.controller("PushList", function($scope, $resource, $timeout){
		var Microbot = $resource('/api/microbots/:id', {id: '@id'}, {
		});

		var MicrobotAction = $resource("/api/microbots/:id/:action", {id: "@id", action: "@action"})
		
		$scope.microbots = {};

		$scope.doAction = (function(uuid, action)
		{
			MicrobotAction.get({id: uuid, action: action});
		});

		$scope.updateName = (function(microbot, newName){
			microbot.name = newName;
			microbot.$save();
		});

		$scope.updateCalibration = (function(microbot, newValue){
			var value = parseFloat(newValue);
			if(!isFinite(value) || value > 1 || value < 0.1)
			{
				// Not a float
				return;
			}
			microbot.calibration = newValue;
			microbot.$save()
		});
		
		function mergeBotList(newList)
		{
			angular.forEach(newList, function(value){
				var key = value.id;
				if($scope.microbots.hasOwnProperty(key))
				{
					angular.copy(value, $scope.microbots[value.id]);
				}
				else
				{
					$scope.microbots[value.id] = value;
				}				
			});
		}

		(function tick() {
	        Microbot.query(function(result){
	        	mergeBotList(result);
	            $timeout(tick, 5000);
	        });
	    })();
	});