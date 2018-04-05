

$(function () {
    var submit_form = function () {
        $.getJSON($SCRIPT_ROOT + "suggest",
            {
                prefix: $('input[name="prefix"]').val(),
                count: $('input[name="count"]').val()

            },
            function (main) {
                $("#listofclusters tbody tr").remove();
                $("#result tbody tr").remove();
                $.each(( main) || [], function (i, item) {
                    link = "#cluster" + String(i + 1);
                    dropdown = "#drop" + String(i + 1);
                    hit = item.top.hits.hits[0];
                    console.log(main);
                    $('#result').append('<tr> <td >' + hit._source.query_4showing + '</td> <td >' + hit._source.count + '</td>  <td class="link" onclick=$('+ '"#cluster' + (i $
                    $('#listofclusters').append('<tr class="header" id=cluster' + String(i + 1) + ' data-type="new"  data-fill="ab" name=' + hit._source.cluster + '> <td colsp$

                }
                );

                $('tr.header').click(function () {

                    if ($(this).attr('data-type') === 'new') {
                        if ($(this).attr('data-fill') === 'ab') {

                            myFunction(this);

                            $(this).attr('data-fill', "500");

console.log('ONE1');                        }
                        else {
                             console.log(this.style.display);
                             console.log($(this).attr('data-fill'));
                            $(this).nextUntil('tr.header').css('display', function (i, v) {


                                  return this.style.display === 'table-row' ? 'none' : 'table-row';
                            });
console.log('TWO2');
                        }
                        }

                    } else {
                        if ($(this).attr('data-fill') === 'ab') {

                            old_myFunction(this);
                            console.log(this.style.display === 'table-row' ? 'none' : 'table-row');
                             $(this).attr('data-fill', "500");
console.log('THREE3');

                        }
                        else {
                            $(this).nextUntil('tr.header').css('display', function (i, v) {
                                return this.style.display === 'table-row' ? 'none' : 'table-row';

                            });
console.log('FOUR4');

                        }
                    }


                });


            });
        $.getJSON($SCRIPT_ROOT + "suggest_old",

            {
                prefix: $('input[name="prefix"]').val()
            },

            function (main) {
                $("#old_listofclusters tbody tr").remove();
                $("#old_result tbody tr").remove();
                $.each((main) || [], function (i, item) {
                    link = "#cluster" + String(i + 1);
                    dropdown = "#drop" + String(i + 1);
                    console.log(item);
   $('#old_result').append('<tr> <td >' + item._source.query + '</td> <td >' + item._source.count + '</td> <td class="link" onclick=$('+ '"#old_cluster' + (i $
                    $('#old_listofclusters').append('<tr class="header" id=old_cluster' + String(i + 1) + ' data-type="old" data-fill="ab" name=' +item._source.cluster + '> <t$

                });

  $('tr.header').click(function () {
                    if ($(this).attr('data-type') === 'new') {

                    } else {
                        if ($(this).attr('data-fill') === 'ab') {

                            old_myFunction(this);
                            $(this).attr('data-fill', "500");
                         console.log('THREE');

                        }
                        else {
                            $(this).nextUntil('tr.header').css('display', function (i, v) {
                                return this.style.display === 'table-row' ? 'none' : 'table-row';
                            });
                    console.log('FOUR');

                        }
                    }


                });

            });

    }

    $("#myId").bind("keyup", function (e) { $("#old_myId").val($("#myId").val()); submit_form() });
    $("#count").bind("input", function (e) { submit_form() });
    $('input[name="prefix"]').focus();

})


function get_description() {

    $.ajax({
        url: $SCRIPT_ROOT + "old_description",
        data: {
            "prefix": $('input[name="prefix"]').val()
        },
        type: 'GET',
        success: function (data) {
            console.log(data);
            $('#description').html(data);
        }
    })
};

function goTo(id) {
console.log(id);
$('html,body').animate({
    scrollTop: ($(id).offset().top)
},500);
};

function myFunction(obj) {
    var number = Number(obj.getAttribute('name'));
    var cluster = Number(number);
    var x = "";
    $.getJSON($SCRIPT_ROOT + "cluster",
        {
            cluster_number: cluster
        },

    function (main) {

            $.each((main.hits && main.hits.hits) || [], function (i, item) {

                var row = document.getElementById('listofclusters').insertRow(obj.rowIndex + 1);
                var cell1 = row.insertCell(0);
                var cell2 = row.insertCell(1);
                var cell3 = row.insertCell(2);
                var cell4 = row.insertCell(3);
                var cell5 = row.insertCell(3);
                cell1.innerHTML = item._source.query_4matching;
                cell2.innerHTML = item._source.count;
                cell3.innerHTML = String(item._source.criteria);
                cell4.innerHTML= item._source.items
                cell5.innerHTML= item._source.query_4showing

            });

        }
    )
};



function old_myFunction(obj) {
    var number = Number(obj.getAttribute('name'));
    var cluster = Number(number);
    var x = "";
    console.log(obj);
    $.getJSON($SCRIPT_ROOT + "old_cluster",
        {
            cluster_number: cluster
        },

        function (main) {

            $.each((main ) || [], function (i, item) {
                var row = document.getElementById('old_listofclusters').insertRow(obj.rowIndex + 1);
                var cell1 = row.insertCell(0);
                var cell2 = row.insertCell(1);
                var cell3 = row.insertCell(2);
                cell1.innerHTML = item._source.query;
                cell2.innerHTML = item._source.count;
            });

        });


};


var rightPane = document.getElementById('right_pane');
var leftPane = document.getElementById('left_pane');
var paneSep = document.getElementById('panes-separator');

// The script below constrains the target to move horizontally between a left and a right virtual boundaries.
// - the left limit is positioned at 10% of the screen width
// - the right limit is positioned at 90% of the screen width
var leftLimit = 5;
var rightLimit = 95;

paneSep.sdrag(function (el, pageX, startX, pageY, startY, fix) {

    fix.skipX = true;
    if (pageX < window.innerWidth * leftLimit / 100) {
        pageX = window.innerWidth * leftLimit / 100;
        fix.pageX = pageX;
    }
    if (pageX > window.innerWidth * rightLimit / 100) {
        pageX = window.innerWidth * rightLimit / 100;
        fix.pageX = pageX;
    }
   }

    var cur = pageX / window.innerWidth * 100;
    if (cur < 0) {
        cur = 0;
    }
    if (cur > window.innerWidth) {
        cur = window.innerWidth;
    }

    var right = (100 - cur - 2);
    leftPane.style.width = cur + '%';
    rightPane.style.width = right + '%';

}, null, 'horizontal');


