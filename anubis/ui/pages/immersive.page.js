/**
 * Created by Nitori on 2017/1/9.
 */
import trianglify from 'trianglify';
import { AutoloadPage } from '../misc/PageLoader';

const immersivePage = new AutoloadPage(null, () => {
    const $header = $('.panel__background');
    if ($header.length === 0) {
        return;
    }
    const background = trianglify({
        width: $header.width(),
        height: $header.height(),
        x_colors: ['#5f2c82', '#49a09d'],
    });
    background.canvas($header.get(0));
    // $header.css('background-image', `url("${background}")`);
});

export default immersivePage;
