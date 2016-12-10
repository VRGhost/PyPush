'use strict';

angular.module("PyPushApp", ["ngResource", 'ui.bootstrap', 'ui.bootstrap.tpls', 'xeditable'])
	.controller("PushList", function($scope, $resource, $timeout, $location){
		var Microbot = $resource('/api/microbots/:id', {id: '@id'}, {
		});

		var MicrobotAction = $resource("/api/microbots/:id/:action", {id: "@id", action: "@action"})
		
		$scope.microbots = {};
		$scope.collapseStatus = {};

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

		$scope.publicEndpointActions = (function(actions){
			var out = [];
			var hiddenActions = ["calibrate"];
			angular.forEach(actions, function(action){
				if(hiddenActions.indexOf(action) < 0)
				{
					out.push(action);
				}
			});
			return out;
		});

		$scope.actionUrl = (function(mb, action){
			var url = "/api/microbots/" + mb.id + "/" + action;
			return $location.protocol() + "://" + $location.host() + ":" + $location.port() + url;
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