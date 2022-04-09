const fs = require('fs');
const XMLHttpRequest = require('xhr2');

const video_id = String(process.argv[2]);
const clientInfo = fs.readFileSync('clientInfo.txt', 'utf8').split('\n');

const logs_path = 'app/resources/downloads/';

if (!fs.existsSync(logs_path)){
    console.log("Creating log directory");
    fs.mkdirSync(logs_path, { recursive: true });
}

var token;

commentMap = {}
chunkMap = {}
cursorMap = {}
cursorQueue = []
chunks = []

var total_comments = 0;
var total_duration;
var logged_duration;

mainFlow();

async function mainFlow() {
    token = await getAccessToken()
    multiThreadDownload(200)
}

// TODO: Fix random slowdown near end of download (not a complete hangup, but significant delay...sometimes)
async function multiThreadDownload(threads) {
    if (!fs.existsSync(video_id)){
        fs.mkdirSync(video_id);
    }

    if (fs.existsSync(`${logs_path}${video_id}.log`)) {
        console.log('Log already exists');
        process.exit(1);
        // Sync

        // 1. Get final cursor from log file (second to last line)
        // 2. Get last logged comment
        // 3. Fetch cursor chunk
        // 4. Start chunk after last logged comment (also store in map)
        // 5. Get timestamp of last comment in fetched chunk
        // 6. Download remaining log starting at offset
        // 7. Append all chunks to existing log (same as before)
    }

    // Download
    const seconds = await getSeconds(video_id);
    const section_dist = seconds / threads
    total_duration = seconds;
    logged_duration = 0;

    showProgress();
    const progressUpdate = setInterval(showProgress, 500);

    var promiseArray = [];

    for (let i=threads; i > 0; i--) {
        offset = section_dist * (i-1);
        //console.log(`Thread ${i} = offset: ${offset}`);
        promiseArray.push(logChunk(i, offset, null));
    }

    await Promise.all(promiseArray);
    logged_duration = total_duration;
    clearInterval(progressUpdate);
    showProgress();
    console.log("Download Complete!")
    //console.log(`total comments: ${total_comments}`)
    //console.log(cursorQueue);

    
    // Sort chunks (by first comment offset)
    chunks = Object.keys(chunkMap).map(function(key) {
        return [key, chunkMap[key]];
    });
    chunks.sort(function(first, second) {
        return first[1] - second[1];
    });

    // Read cursor of second to last chunk, append to end of last chunk
    const chunkFileToCopy = `${video_id}/${chunks[chunks.length - 2][0]}`;
    const chunkToCopy = readFile(chunkFileToCopy);
    //console.log(chunkToCopy);
    lines = chunkToCopy.split("\n");
    cursorToCopy = lines[lines.length - 2] + "\n";
    //console.log(cursorToCopy);

    const chunkFileToUpdate = `${video_id}/${chunks[chunks.length - 1][0]}`;
    const chunkToUpdate = readFile(chunkFileToUpdate);
    lines = chunkToUpdate.split("\n");
    lines[lines.length - 1] = cursorToCopy;
    let updatedChunk = lines.join("\n");
    //console.log(updatedChunk);
    writeFile(chunkFileToUpdate, updatedChunk)
    

    // Stitch together chunk files
    await stitchLogs(video_id);

     // Cleanup
     if (fs.existsSync(video_id)) {
        fs.rmSync(video_id, { recursive: true, force: true });
    }

    console.log("_EOS_")
    //console.log("DONE!");
}

function writeFile(file, content) {
    if (content == '') {
        return;
    }

    fs.writeFileSync(file, content);
}

function readFile(file) {
    return fs.readFileSync(file, {encoding:'utf8', flag:'r'});
}

function appendFile(dest_file, source_file) {
    const data = readFile(source_file);
    appendData(dest_file, data);
}

function appendData(dest_file, data) {
    fs.appendFileSync(dest_file, data);
}

async function stitchLogs() {
    const dest_file = `${logs_path}${video_id}.log`;

    for (chunk of chunks) {
        const source_file = `${video_id}/${chunk[0]}`;
        appendFile(dest_file, source_file);
    }

    return;
}

async function logChunk(thread, offset, cursor) {
    try {
        response = null;
        if (offset != null) {
            response = await getOffsetComments(video_id, offset)
        } 
        else if (cursor != null) {
            if (!cursorMap.hasOwnProperty(cursor)) {
                cursorMap[next_cursor] = thread;
                response = await getCursorComments(video_id, cursor)
            } else {
                console.log('repeat cursor');
                return;
            }
            //console.log(response)
        }
        if (response == null) {
            //console.log(`${thread}: REACHED END OF COMMENTS`);
            return 0;
        }
        comments = null;
        try {
            comments = response['comments'];
        } catch {
            console.log(response);
        }
    
        if (comments != null) {
            stop = true;
            chunk_id = comments[0]['_id'];
            comment_offset = comments[0]['content_offset_seconds'];

            if (!commentMap.hasOwnProperty(chunk_id)) {
                if (!chunkMap.hasOwnProperty(chunk_id)) {
                    chunkMap[chunk_id] = parseFloat(comment_offset);
                    stop = false;
                }
            }

            if (stop) {
                return;
            }

            content = '';
            for (comment of comments) {
                comment_id = comment['_id'];
                if (commentMap.hasOwnProperty(comment_id)) {
                    //console.log(`${thread}: REACHED END OF SECTION`);
                    //console.log(`Hit comment logged by: ${commentMap[comment['_id']]}`)
                    stop = true;
                    break;
                } else {
                    commentMap[comment_id] = parseFloat(comment_offset);
                }

                last_comment_offset = comment['content_offset_seconds'];
                seconds = parseInt(last_comment_offset);
                comment_line = `[${toTimestamp(seconds)}] <${comment['commenter']['display_name']}> ${comment['message']['body']}`;
                content += comment_line + "\n";
                total_comments += 1;
                //console.log(comment_line);
            }

            next_cursor = response['_next'];

            if (next_cursor) {
                content += next_cursor + "\n"; //next_cursor + " " + comment_offset + "\n";
            }
            
            try {
            writeFile(`${video_id}/${chunk_id}`, content);
            } catch (err) {
                console.log('write error');
                console.log(err);
            }

            logged_duration += (parseFloat(last_comment_offset) - parseFloat(comment_offset));

            if (stop) {
                return;
            }

            
            //next_cursor = cursorQueue.shift();
            
            if (next_cursor) {
                await logChunk(thread, null, next_cursor);
            } else {
                //console.log(next_cursor);
            }

            /*
            if (next_cursor) {
                //console.log(`Thread ${thread} taking cursor ${next_cursor}`)
                await logChunk(thread, video_id, null, next_cursor);
            }
            */
            
            //cursor = response['_next'];
            //await logChunk(thread, video_id, null, cursor);
        //console.log(`Thread ${thread} is returning`)
        } 
    } catch (error) {
        console.log(error);
    }
}

async function showProgress()
{
    process.stdout.write(`Downloading: ${roundTo(2, (logged_duration/total_duration) * 100)}%` + "\n"); //+ "\r"
}

// TODO: Cache access token?
async function getAccessToken() {
    var url = new URL(`https://id.twitch.tv/oauth2/token`);
    url.searchParams.append('client_id', clientInfo[0]);
    url.searchParams.append('client_secret', clientInfo[1]);
    url.searchParams.append('grant_type', 'client_credentials');

    let xhr = createRequest("POST", url.toString(), false);
    response = await submitRequest(xhr);

    return JSON.parse(response);
}

async function getSeconds() {
    var url = new URL(`https://api.twitch.tv/helix/videos`);
    url.searchParams.append('id', video_id);

    let xhr = createRequest("GET", url.toString(), false);
    xhr.setRequestHeader('Client-ID', clientInfo[0]);
    xhr.setRequestHeader('Authorization', 'Bearer ' + token['access_token']);

    response = await submitRequest(xhr);
    var obj = JSON.parse(response);
    var duration = obj['data'][0]['duration'];
   
    return toSeconds(duration);
}

async function getOffsetComments(video_id, offset) {
    var url = new URL(`https://api.twitch.tv/v5/videos/${video_id}/comments`);
    url.searchParams.append('content_offset_seconds', offset);
    
    let xhr = createRequest("GET", url.toString(), true);

    return JSON.parse(await submitRequest(xhr));
}

async function getCursorComments(video_id, cursor) {
    var url = new URL(`https://api.twitch.tv/v5/videos/${video_id}/comments`);
    url.searchParams.append('cursor', cursor);
    
    let xhr = createRequest("GET", url.toString(), true);
    
    return JSON.parse(await submitRequest(xhr));
}

function createRequest(type, url, default_headers) {
    let xhr = new XMLHttpRequest();

    xhr.open(type, url);

    if (default_headers) {
        xhr.setRequestHeader("Accept", "application/vnd.twitchtv.v5+json");
        xhr.setRequestHeader("Client-ID", "kimne78kx3ncx6brgo4mv6wki5h1ko");
        //xhr.setRequestHeader('Cache-Control', 'no-cache');
    }

    return xhr;
}

function submitRequest(xhr) {
    return new Promise(function (resolve, reject) {
        xhr.onload = function () {
            if (this.status == 200) { //this.status >= 200 && this.status < 300
                //console.log(this.status);
                resolve(xhr.response);
            } else {
                resolve(xhr.response);
                console.log('FAIL RESPONSE')
                console.log(response);
                reject({
                    status: this.status,
                    statusText: xhr.statusText
                });
            }
        };
        xhr.onerror = function () {
            reject({
                status: this.status,
                statusText: xhr.statusText
            });
        };
        xhr.send();
    });
  }

  function toSeconds(duration) {
    if (duration.indexOf('h') == -1) {
        duration = '0h' + duration;
    }
    duration = duration.replace('h', ':').replace('m', ':').replace('s', '');
    parts = duration.split(':');

    return 3600 * parseInt(parts[0]) + 60 * parseInt(parts[1]) + parseInt(parts[2]);;
  }

// TODO: Handle times above 24 hours
function toTimestamp(seconds) {
    return new Date(1000 * seconds).toISOString().substr(11, 8)
}

function roundTo(places, num) {    
    return +(Math.round(num + `e+${places}`)  + `e-${places}`);
}