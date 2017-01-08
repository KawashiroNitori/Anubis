/**
 * Created by Nitori on 2017/1/5.
 */
import trianglify from 'trianglify';
import { AutoloadPage } from '../../misc/PageLoader';

const headerPage = new AutoloadPage(null, () => {
    const $header = $('.header__background');
    const background = trianglify({
        width: $header.width(),
        height: $header.height(),
        x_colors: ['#000', '#fff'],
    });
    background.canvas($header.get(0));
    // $header.css('background-image', `url("${background}")`);
});

export default headerPage;
